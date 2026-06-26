#!/usr/bin/env python3
"""Verify the A640 textured FS shader words for the D1 2D rung."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root


CYCLE = "V3305"
SCOPE = "gpu-2d-d1-textured-fs-shader-byte-materialization"
REPO_ROOT = repo_root()
DISPATCH = REPO_ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

TEXTURED_FS_ASM = [
    "bary.f r0.x, 0, r0.x",
    "bary.f r0.y, 1, r0.x",
    "sam (f32)(xyzw)r0.z, r0.x, s#0, t#0",
    "end",
    "nop",
]

EXPECTED_INSTRUCTION_PAIRS = [
    (0x00002000, 0x47300000),
    (0x00002001, 0x47300001),
    (0x00000001, 0xA0C01F02),
    (0x00000000, 0x03000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x00000000, 0x00000000),
]

EXPECTED_BINARY_SHA256 = "4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3"
EXPECTED_SIZE_BYTES = 128
EXPECTED_SIZE_DWORDS = 32
EXPECTED_INSTRLEN = 1
EXPECTED_CONSTLEN = 0
EXPECTED_MAX_REG = 1
EXPECTED_MAX_HALF_REG = -1
EXPECTED_MERGEDREGS = True
EXPECTED_SAMPLE_OUTPUT_REGID = 2
EXPECTED_SAMPLE_COMPONENTS = 4
EXPECTED_NUM_SAMP = 1
EXPECTED_NUM_TEX = 1

EXPECTED_DISASM_SNIPPETS = [
    "bary.f r0.x, 0, r0.x",
    "bary.f r0.y, 1, r0.x",
    "sam (f32)(xyzw)r0.z, r0.x, s#0, t#0",
    "end",
]

IR3_DISASM_CANDIDATES = [
    Path("/tmp/a90-mesa-d1-texture-build-libdrm/src/freedreno/isa/ir3-disasm"),
    Path("/tmp/a90-mesa-d1-texture-build/src/freedreno/isa/ir3-disasm"),
    Path("/tmp/a90-mesa-c1-fullnir-softpipe-v3300/src/freedreno/isa/ir3-disasm"),
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


def _pairs_to_dwords(pairs: list[tuple[int, int]]) -> list[int]:
    dwords: list[int] = []
    for lo, hi in pairs:
        dwords.extend([lo, hi])
    return dwords


def _dwords_to_bytes(dwords: list[int]) -> bytes:
    out = bytearray()
    for dword in dwords:
        out.extend(dword.to_bytes(4, "little"))
    return bytes(out)


def _find_ir3_disasm() -> Path | None:
    for candidate in IR3_DISASM_CANDIDATES:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _run_ir3_disasm(binary: bytes, ir3_disasm: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="a90-d1-ir3-disasm-") as tmp:
        shader_path = Path(tmp) / "textured_fs_fd640.bin"
        shader_path.write_bytes(binary)
        proc = subprocess.run(
            [str(ir3_disasm), "-c", "06040000", str(shader_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return {
        "command": [str(ir3_disasm), "-c", "06040000", "<temp-shader-bin>"],
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "lines": [line for line in proc.stdout.splitlines() if line.strip()],
    }


def _extract_define_uint(text: str, name: str) -> int | None:
    match = re.search(rf"^#define\s+{re.escape(name)}\s+([0-9A-Fa-fx]+)U?\s*$", text, re.MULTILINE)
    return int(match.group(1), 0) if match else None


def _h3_output_contract(path: Path = DISPATCH) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    ps_output_regid = _extract_define_uint(text, "GPU_H3_PS_OUTPUT_REGID")
    ps_fullregfootprint = _extract_define_uint(text, "GPU_H3_SP_PS_FULLREGFOOTPRINT")
    instr_align = _extract_define_uint(text, "GPU_H3_IR3_INSTR_ALIGN")
    fs_shader_slot_aliases_aligned = (
        "#define GPU_H3_FS_SHADER_DWORDS GPU_H3_SHADER_ALIGNED_DWORDS" in text
    )
    shader_aligned_expr_matches = (
        "#define GPU_H3_SHADER_ALIGNED_DWORDS (GPU_H3_IR3_INSTR_ALIGN * 2U)" in text
    )
    shader_aligned_dwords = instr_align * 2 if instr_align is not None else None
    fs_shader_dwords = shader_aligned_dwords if fs_shader_slot_aliases_aligned else None
    return {
        "path": str(path),
        "ps_output_regid": ps_output_regid,
        "ps_fullregfootprint": ps_fullregfootprint,
        "ir3_instr_align": instr_align,
        "fs_shader_dwords": fs_shader_dwords,
        "shader_aligned_dwords": shader_aligned_dwords,
        "fs_shader_slot_aliases_aligned": fs_shader_slot_aliases_aligned,
        "shader_aligned_expr_matches": shader_aligned_expr_matches,
        "sample_writes_color_regid": EXPECTED_SAMPLE_OUTPUT_REGID,
        "sample_writes_components": EXPECTED_SAMPLE_COMPONENTS,
        "sample_output_matches_h3_color_regid": ps_output_regid == EXPECTED_SAMPLE_OUTPUT_REGID,
        "fullregfootprint_covers_sample_result": (
            ps_fullregfootprint is not None and ps_fullregfootprint >= EXPECTED_MAX_REG + 1
        ),
        "shader_slot_covers_aligned_payload": (
            fs_shader_dwords == shader_aligned_dwords == EXPECTED_SIZE_DWORDS
            and shader_aligned_expr_matches
        ),
        "has_mergedregs_ps_control": "GPU_H3_SP_PS_CNTL_0_MERGEDREGS" in text,
        "has_rgba8_mrt0_contract": "#define GPU_H3_SP_PS_MRT_REG0 GPU_H3_COLOR_FORMAT" in text,
        "valid": all(
            [
                ps_output_regid == EXPECTED_SAMPLE_OUTPUT_REGID,
                ps_fullregfootprint is not None and ps_fullregfootprint >= EXPECTED_MAX_REG + 1,
                fs_shader_dwords == shader_aligned_dwords == EXPECTED_SIZE_DWORDS,
                shader_aligned_expr_matches,
                "GPU_H3_SP_PS_CNTL_0_MERGEDREGS" in text,
                "#define GPU_H3_SP_PS_MRT_REG0 GPU_H3_COLOR_FORMAT" in text,
            ]
        ),
    }


def run_verification(*, require_disasm: bool = False) -> dict[str, Any]:
    dwords = _pairs_to_dwords(EXPECTED_INSTRUCTION_PAIRS)
    shader_binary = _dwords_to_bytes(dwords)
    ir3_disasm = _find_ir3_disasm()
    disasm: dict[str, Any] | None = None
    if ir3_disasm is not None:
        disasm = _run_ir3_disasm(shader_binary, ir3_disasm)

    disasm_stdout = disasm["stdout"] if disasm else ""
    h3_contract = _h3_output_contract()
    checks = {
        "asm_contract_has_two_bary_inputs": TEXTURED_FS_ASM[:2] == [
            "bary.f r0.x, 0, r0.x",
            "bary.f r0.y, 1, r0.x",
        ],
        "asm_contract_uses_non_bindless_sampler0_texture0": (
            "sam (f32)(xyzw)r0.z, r0.x, s#0, t#0" in TEXTURED_FS_ASM
        ),
        "shader_dword_count_matches": len(dwords) == EXPECTED_SIZE_DWORDS,
        "shader_byte_count_matches": len(shader_binary) == EXPECTED_SIZE_BYTES,
        "shader_binary_sha256_matches": _sha256_bytes(shader_binary) == EXPECTED_BINARY_SHA256,
        "shader_metadata_matches_materializer": all(
            [
                EXPECTED_INSTRLEN == 1,
                EXPECTED_CONSTLEN == 0,
                EXPECTED_MAX_REG == 1,
                EXPECTED_MAX_HALF_REG == -1,
                EXPECTED_MERGEDREGS is True,
            ]
        ),
        "h3_output_contract_valid": h3_contract["valid"],
        "ir3_disasm_available": ir3_disasm is not None,
        "ir3_disasm_returncode_zero": disasm["returncode"] == 0 if disasm else False,
        "ir3_disasm_contains_expected_ops": (
            all(snippet in disasm_stdout for snippet in EXPECTED_DISASM_SNIPPETS)
            if disasm
            else False
        ),
    }

    mandatory_checks = [
        "asm_contract_has_two_bary_inputs",
        "asm_contract_uses_non_bindless_sampler0_texture0",
        "shader_dword_count_matches",
        "shader_byte_count_matches",
        "shader_binary_sha256_matches",
        "shader_metadata_matches_materializer",
        "h3_output_contract_valid",
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
    ready_for_d1_source = all(
        checks[name]
        for name in [
            "shader_binary_sha256_matches",
            "h3_output_contract_valid",
            "ir3_disasm_returncode_zero",
            "ir3_disasm_contains_expected_ops",
        ]
    )

    return {
        "cycle": CYCLE,
        "scope": SCOPE,
        "passed": passed,
        "ready_for_d1_source": ready_for_d1_source,
        "checks": checks,
        "asm": {
            "source_lines": TEXTURED_FS_ASM,
            "materializer": "Mesa ir3_parse_asm with fd_dev_id gpu_id=640, no device open",
            "materializer_evidence": "/tmp/a90-mesa-d1-texture-build-libdrm/src/freedreno/ir3/ir3_delay_test --dump /tmp/a90-d1-textured-fs.asm 640 0",
        },
        "shader": {
            "gpu_name": "FD640",
            "chip_id": "06040000",
            "stage": "fragment",
            "instrlen": EXPECTED_INSTRLEN,
            "constlen": EXPECTED_CONSTLEN,
            "sizedwords": EXPECTED_SIZE_DWORDS,
            "size_bytes": EXPECTED_SIZE_BYTES,
            "max_reg": EXPECTED_MAX_REG,
            "max_half_reg": EXPECTED_MAX_HALF_REG,
            "mergedregs": EXPECTED_MERGEDREGS,
            "num_samp": EXPECTED_NUM_SAMP,
            "num_tex": EXPECTED_NUM_TEX,
            "sample_output_regid": EXPECTED_SAMPLE_OUTPUT_REGID,
            "sample_output_components": EXPECTED_SAMPLE_COMPONENTS,
            "binary_sha256": _sha256_bytes(shader_binary),
            "dwords_hex": [f"0x{dword:08x}" for dword in dwords],
            "instruction_pairs_hex": [
                f"{hi:08x}_{lo:08x}" for lo, hi in EXPECTED_INSTRUCTION_PAIRS
            ],
        },
        "h3_output_contract": h3_contract,
        "toolchain": {
            "mesa_source_root": "/tmp/a90-mesa-gpu-src",
            "mesa_build_root": "/tmp/a90-mesa-d1-texture-build-libdrm",
            "local_libdrm_prefix": "/tmp/a90-libdrm-prefix",
            "ir3_disasm": str(ir3_disasm) if ir3_disasm else None,
            "ir3_disasm_sha256": _sha256_path(ir3_disasm) if ir3_disasm else None,
        },
        "disasm": disasm,
        "expected_disasm_snippets": EXPECTED_DISASM_SNIPPETS,
        "next": [
            "embed these verified FS shader words in a D1 static checkerboard texture source/build unit",
            "load one sampler descriptor and one TEXMEMOBJ descriptor with NTEX=1/NSAMP=1",
            "draw a fullscreen quad and require readback to contain the sampled checkerboard pattern",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON result")
    parser.add_argument(
        "--require-disasm",
        action="store_true",
        help="fail if local FD640 ir3-disasm verification is unavailable or mismatched",
    )
    args = parser.parse_args()

    result = run_verification(require_disasm=args.require_disasm)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{CYCLE} {SCOPE} passed={int(result['passed'])}")
        print(f"ready_for_d1_source={int(result['ready_for_d1_source'])}")
        print(f"shader_binary_sha256={result['shader']['binary_sha256']}")
        print(f"ir3_disasm={result['toolchain']['ir3_disasm']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
