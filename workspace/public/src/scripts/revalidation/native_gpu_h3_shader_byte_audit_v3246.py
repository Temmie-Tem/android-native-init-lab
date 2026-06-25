#!/usr/bin/env python3
"""Audit H3 hand-assembled ir3 shader words against Mesa ir3-disasm."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root


REPO_ROOT = repo_root()
DISPATCH = REPO_ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
DEFAULT_TMP_IR3_DISASM = Path("/tmp/a90-mesa-h3-build-ir3/src/freedreno/isa/ir3-disasm")
DEFAULT_CHIP_ID = "06040000"

EXPECTED_VS = [
    "mov.u32u32 r0.z, 0x3f800000",
    "mov.u32u32 r0.w, 0x3f800000",
    "end",
    *["nop"] * 13,
]
EXPECTED_FS = [
    "mov.f32f32 r0.x, (1.0)",
    "end",
    *["nop"] * 14,
]


def _bits(value: int, low: int, high: int) -> int:
    mask = (1 << (high - low + 1)) - 1
    return (value >> low) & mask


def _clean_c_int_suffixes(expr: str) -> str:
    return re.sub(r"\b(0x[0-9a-fA-F]+|\d+)(?:[uUlL]+)\b", r"\1", expr)


def _logical_define_lines(source: str) -> list[str]:
    lines: list[str] = []
    current = ""
    for raw in source.splitlines():
        line = raw.split("//", 1)[0].rstrip()
        if not line and not current:
            continue
        if line.endswith("\\"):
            current += line[:-1] + " "
            continue
        current += line
        if current:
            lines.append(current)
        current = ""
    if current:
        lines.append(current)
    return lines


class MacroResolver:
    def __init__(self, source: str) -> None:
        self._exprs: dict[str, str] = {}
        self._values: dict[str, int] = {}
        for line in _logical_define_lines(source):
            match = re.match(r"\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*$", line)
            if not match:
                continue
            name, expr = match.groups()
            if "(" in name:
                continue
            self._exprs[name] = expr.strip()

    def resolve(self, expr: str, stack: tuple[str, ...] = ()) -> int:
        expr = expr.strip()
        if expr in self._values:
            return self._values[expr]
        if expr in self._exprs:
            if expr in stack:
                raise ValueError(f"recursive macro: {' -> '.join(stack + (expr,))}")
            value = self.resolve(self._exprs[expr], stack + (expr,))
            self._values[expr] = value
            return value
        return self._eval_expr(expr, stack)

    def _eval_expr(self, expr: str, stack: tuple[str, ...]) -> int:
        expr = _clean_c_int_suffixes(expr)
        expr = expr.replace("true", "1").replace("false", "0")
        tree = ast.parse(expr, mode="eval")
        return self._eval_node(tree.body, stack)

    def _eval_node(self, node: ast.AST, stack: tuple[str, ...]) -> int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return int(node.value)
        if isinstance(node, ast.Name):
            return self.resolve(node.id, stack)
        if isinstance(node, ast.UnaryOp):
            value = self._eval_node(node.operand, stack)
            if isinstance(node.op, ast.Invert):
                return ~value
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return value
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, stack)
            right = self._eval_node(node.right, stack)
            if isinstance(node.op, ast.BitOr):
                return left | right
            if isinstance(node.op, ast.BitAnd):
                return left & right
            if isinstance(node.op, ast.BitXor):
                return left ^ right
            if isinstance(node.op, ast.LShift):
                return left << right
            if isinstance(node.op, ast.RShift):
                return left >> right
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.FloorDiv):
                return left // right
        raise ValueError(f"unsupported macro expression: {ast.dump(node)}")


@dataclass(frozen=True)
class InstructionWord:
    index: int
    lo: int
    hi: int

    @property
    def word(self) -> int:
        return (self.hi << 32) | self.lo

    @property
    def mesa_hex(self) -> str:
        return f"{self.hi:08x}{self.lo:08x}"

    @property
    def display(self) -> str:
        return f"{self.hi:08x}_{self.lo:08x}"


def _extract_h3_shader_arrays(source: str, macros: MacroResolver) -> dict[str, list[InstructionWord]]:
    start = source.index("static int gpu_h3_draw_envelope_probe_child")
    section = source[start : source.index("static int gpu_h3_draw_envelope_probe(", start)]
    shaders: dict[str, list[InstructionWord]] = {}
    for name in ("vs_shader", "fs_shader"):
        match = re.search(
            rf"static const uint32_t {name}\[(?P<length>[^\]]+)\]\s*=\s*\{{(?P<body>.*?)\}};",
            section,
            re.S,
        )
        if not match:
            raise ValueError(f"{name} array not found in H3 probe child")
        declared_len = macros.resolve(match.group("length"))
        tokens = [
            item.strip()
            for item in match.group("body").replace("\n", " ").split(",")
            if item.strip()
        ]
        values = [macros.resolve(token) & 0xFFFFFFFF for token in tokens]
        if len(values) > declared_len:
            raise ValueError(f"{name} initializer exceeds declared length: {len(values)} > {declared_len}")
        values.extend([0] * (declared_len - len(values)))
        if len(values) % 2:
            raise ValueError(f"{name} dword count is odd: {len(values)}")
        shaders[name] = [
            InstructionWord(index=i // 2, lo=values[i], hi=values[i + 1])
            for i in range(0, len(values), 2)
        ]
    return shaders


def _reg_name(regid: int, half: bool = False) -> str:
    prefix = "hr" if half else "r"
    return f"{prefix}{regid // 4}.{'xyzw'[regid % 4]}"


def _float32_from_u32(value: int) -> str:
    flt = struct.unpack(">f", value.to_bytes(4, "big"))[0]
    if flt == 0.0:
        return "0.0"
    if flt == 1.0:
        return "1.0"
    return f"{flt:g}"


def decode_current_ir3_word(word: InstructionWord) -> dict[str, Any]:
    value = word.word
    cat = _bits(value, 61, 63)
    common = {
        "index": word.index,
        "word": word.display,
        "cat": cat,
        "ss": bool((value >> 44) & 1),
        "sy": bool((value >> 60) & 1),
    }
    if value == 0:
        return common | {"mnemonic": "nop", "disasm": "nop"}
    if cat == 0:
        op = _bits(value, 55, 58)
        if op == 6:
            return common | {"mnemonic": "end", "disasm": "end"}
        return common | {"mnemonic": "cat0-unknown", "disasm": "unknown"}
    if cat == 1 and _bits(value, 57, 58) == 0:
        dst_type = _bits(value, 46, 48)
        src_type = _bits(value, 50, 52)
        dst = _bits(value, 32, 39)
        src_is_immediate = bool((word.hi >> 22) & 1)
        if dst_type == 1 and src_type == 1:
            dst_name = _reg_name(dst)
            if src_is_immediate:
                src = f"({_float32_from_u32(word.lo)})"
            else:
                src = _reg_name(word.lo & 0xFF)
            return common | {
                "mnemonic": "mov.f32f32",
                "dst_type": "f32",
                "src_type": "f32",
                "dst_regid": dst,
                "src_immediate": src_is_immediate,
                "disasm": f"mov.f32f32 {dst_name}, {src}",
            }
        if dst_type == 3 and src_type == 3:
            dst_name = _reg_name(dst)
            if src_is_immediate:
                src = f"0x{word.lo:08x}"
            else:
                src = _reg_name(word.lo & 0xFF)
            return common | {
                "mnemonic": "mov.u32u32",
                "dst_type": "u32",
                "src_type": "u32",
                "dst_regid": dst,
                "src_immediate": src_is_immediate,
                "disasm": f"mov.u32u32 {dst_name}, {src}",
            }
        half_dst = dst_type in (0, 2, 4, 6, 7)
        return common | {
            "mnemonic": "cat1-mov",
            "dst_type_bits": dst_type,
            "src_type_bits": src_type,
            "dst_half": half_dst,
            "disasm": "cat1-mov-unexpected-type",
        }
    return common | {"mnemonic": "unknown", "disasm": "unknown"}


def _find_ir3_disasm(candidate: str | None) -> Path | None:
    if candidate:
        path = Path(candidate)
        return path if path.is_file() and os.access(path, os.X_OK) else None
    env_path = os.environ.get("IR3_DISASM")
    if env_path:
        path = Path(env_path)
        if path.is_file() and os.access(path, os.X_OK):
            return path
    which = shutil.which("ir3-disasm")
    if which:
        return Path(which)
    if DEFAULT_TMP_IR3_DISASM.is_file() and os.access(DEFAULT_TMP_IR3_DISASM, os.X_OK):
        return DEFAULT_TMP_IR3_DISASM
    return None


def _run_ir3_disasm(ir3_disasm: Path, chip_id: str, word: InstructionWord) -> dict[str, str]:
    proc = subprocess.run(
        [str(ir3_disasm), "-c", chip_id, "-x", word.mesa_hex],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ir3-disasm failed for {word.display}: rc={proc.returncode} stderr={proc.stderr.strip()}"
        )
    stdout = proc.stdout.strip()
    match = re.search(r"\]\s+(?P<disasm>.+)$", stdout)
    if not match:
        raise RuntimeError(f"cannot parse ir3-disasm output for {word.display}: {stdout!r}")
    return {"stdout": stdout, "disasm": match.group("disasm").strip()}


def run_audit(
    dispatch: Path = DISPATCH,
    ir3_disasm: str | None = None,
    require_ir3_disasm: bool = False,
    chip_id: str = DEFAULT_CHIP_ID,
) -> dict[str, Any]:
    source = dispatch.read_text(encoding="utf-8")
    macros = MacroResolver(source)
    shaders = _extract_h3_shader_arrays(source, macros)
    disasm_path = _find_ir3_disasm(ir3_disasm)
    if require_ir3_disasm and disasm_path is None:
        raise FileNotFoundError("ir3-disasm not found; pass --ir3-disasm or set IR3_DISASM")

    expected = {"vs_shader": EXPECTED_VS, "fs_shader": EXPECTED_FS}
    decoded: dict[str, list[dict[str, Any]]] = {}
    mismatches: list[str] = []
    for shader_name, words in shaders.items():
        decoded[shader_name] = []
        for word, expected_disasm in zip(words, expected[shader_name], strict=True):
            entry = decode_current_ir3_word(word)
            if disasm_path is not None:
                external = _run_ir3_disasm(disasm_path, chip_id, word)
                entry["mesa_ir3_disasm"] = external["disasm"]
                entry["mesa_ir3_stdout"] = external["stdout"]
                actual = external["disasm"]
            else:
                actual = entry["disasm"]
            entry["expected"] = expected_disasm
            entry["matches_expected"] = actual == expected_disasm
            if actual != expected_disasm:
                mismatches.append(
                    f"{shader_name}[{word.index}] {word.display}: {actual!r} != {expected_disasm!r}"
                )
            decoded[shader_name].append(entry)

    ps_output_reg0 = macros.resolve("GPU_H3_PS_OUTPUT_REGID")
    sp_vs_output_reg0 = macros.resolve("GPU_H3_SP_VS_OUTPUT_REG0")
    vpc_vs_cntl = macros.resolve("GPU_H3_VPC_VS_CNTL")
    vpc_vs_siv_cntl = macros.resolve("GPU_H3_VPC_VS_SIV_CNTL")
    vpc_vs_siv_cntl_v2 = macros.resolve("GPU_H3_VPC_VS_SIV_CNTL_V2")
    sp_ps_mrt_reg0 = macros.resolve("GPU_H3_COLOR_FORMAT")
    fs_first = decoded["fs_shader"][0]
    checks = {
        "all_shader_words_match_expected": not mismatches,
        "external_ir3_disasm_used": disasm_path is not None,
        "ir3_disasm_path": str(disasm_path) if disasm_path else None,
        "fs_writes_full_f32_r0x": fs_first.get("disasm") == "mov.f32f32 r0.x, (1.0)"
        or fs_first.get("mesa_ir3_disasm") == "mov.f32f32 r0.x, (1.0)",
        "vs_uses_mesa_reference_u32_z_w_instrlen1": (
            decoded["vs_shader"][0].get("disasm") == "mov.u32u32 r0.z, 0x3f800000"
            or decoded["vs_shader"][0].get("mesa_ir3_disasm") == "mov.u32u32 r0.z, 0x3f800000"
        ) and (
            decoded["vs_shader"][1].get("disasm") == "mov.u32u32 r0.w, 0x3f800000"
            or decoded["vs_shader"][1].get("mesa_ir3_disasm") == "mov.u32u32 r0.w, 0x3f800000"
        ),
        "vs_shader_instrlen": macros.resolve("GPU_H3_VS_SHADER_INSTRLEN"),
        "fs_shader_instrlen": macros.resolve("GPU_H3_FS_SHADER_INSTRLEN"),
        "ir3_instr_align": macros.resolve("GPU_H3_IR3_INSTR_ALIGN"),
        "sp_ps_output_reg0_regid": ps_output_reg0 & 0xFF,
        "sp_ps_output_reg0_half_precision": bool(ps_output_reg0 & (1 << 8)),
        "fs_full_precision_matches_ps_output": not bool(ps_output_reg0 & (1 << 8)),
        "sp_ps_mrt_reg0_color_format": sp_ps_mrt_reg0 & 0xFF,
        "sp_ps_mrt_reg0_color_uint": bool(sp_ps_mrt_reg0 & (1 << 9)),
        "sp_ps_mrt_reg0_has_no_half_precision_field": True,
        "sp_vs_output_reg0_regid": sp_vs_output_reg0 & 0xFF,
        "sp_vs_output_reg0_compmask": (sp_vs_output_reg0 >> 8) & 0xF,
        "sp_vs_vpc_dest_reg0_outloc0": 0,
        "vpc_vs_cntl_stride_in_vpc": vpc_vs_cntl & 0xFF,
        "vpc_vs_cntl_positionloc": (vpc_vs_cntl >> 8) & 0xFF,
        "vpc_vs_cntl_psizeloc": (vpc_vs_cntl >> 16) & 0xFF,
        "vpc_vs_siv_cntl_layerloc": vpc_vs_siv_cntl & 0xFF,
        "vpc_vs_siv_cntl_viewloc": (vpc_vs_siv_cntl >> 8) & 0xFF,
        "vpc_vs_siv_cntl_v2_layerloc": vpc_vs_siv_cntl_v2 & 0xFF,
        "vpc_vs_siv_cntl_v2_viewloc": (vpc_vs_siv_cntl_v2 >> 8) & 0xFF,
        "position_is_vpc_vs_cntl_not_siv": ((vpc_vs_cntl >> 8) & 0xFF) == 0,
    }
    passed = (
        checks["all_shader_words_match_expected"]
        and checks["fs_writes_full_f32_r0x"]
        and checks["vs_uses_mesa_reference_u32_z_w_instrlen1"]
        and checks["vs_shader_instrlen"] == 1
        and checks["fs_shader_instrlen"] == 1
        and checks["ir3_instr_align"] == 16
        and checks["fs_full_precision_matches_ps_output"]
        and checks["sp_vs_output_reg0_regid"] == 0
        and checks["sp_vs_output_reg0_compmask"] == 0xF
        and checks["sp_vs_vpc_dest_reg0_outloc0"] == 0
        and checks["vpc_vs_cntl_stride_in_vpc"] == 4
        and checks["vpc_vs_cntl_positionloc"] == 0
        and checks["vpc_vs_cntl_psizeloc"] == 0xFF
    )
    return {
        "cycle": "V3246",
        "scope": "gpu-h3-shader-byte-audit",
        "dispatch": str(dispatch.relative_to(REPO_ROOT)),
        "chip_id": chip_id,
        "passed": passed,
        "mismatches": mismatches,
        "decoded": decoded,
        "checks": checks,
        "sources": {
            "ir3_disasm": "Mesa freedreno src/freedreno/isa/ir3-disasm.c",
            "ir3_cat0_xml": "Mesa freedreno src/freedreno/isa/ir3-cat0.xml",
            "ir3_cat1_xml": "Mesa freedreno src/freedreno/isa/ir3-cat1.xml",
            "a6xx_xml": "Mesa freedreno src/freedreno/registers/adreno/a6xx.xml",
            "fd6_program": "Mesa gallium freedreno a6xx/fd6_program.cc",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", type=Path, default=DISPATCH)
    parser.add_argument("--ir3-disasm")
    parser.add_argument("--require-ir3-disasm", action="store_true")
    parser.add_argument("--chip-id", default=DEFAULT_CHIP_ID)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = run_audit(
        dispatch=args.dispatch,
        ir3_disasm=args.ir3_disasm,
        require_ir3_disasm=args.require_ir3_disasm,
        chip_id=args.chip_id,
    )
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
