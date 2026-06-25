#!/usr/bin/env python3
"""Diff current H3 state against the local A640 freedreno cffdump triangle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from native_gpu_h3_shader_byte_audit_v3246 import MacroResolver


CYCLE = "V3286"
SCOPE = "gpu-h3-cffdump-current-state-diff"
REPO_ROOT = repo_root()
DISPATCH = REPO_ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
DEFAULT_SUMMARY = Path("/tmp/a90-h3-cffdump/triangle_summary.txt")
DEFAULT_RD = Path("/tmp/a90-h3-cffdump/triangle_list.rd")

REGISTER_LINE_RE = re.compile(
    r"^\s*[!+? ]*\s*(?P<value>[0-9a-fA-F]{8})\s+"
    r"(?P<name>[A-Z0-9_]+(?:\[[^\]]+\])?(?:\.[A-Z0-9_]+(?:\[[^\]]+\])?)*)\s*:"
)


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _normalize_reg_name(name: str) -> str:
    def repl(match: re.Match[str]) -> str:
        raw = match.group(1)
        value = int(raw, 16) if raw.lower().startswith("0x") else int(raw, 10)
        return f"[{value}]"

    return re.sub(r"\[(0x[0-9a-fA-F]+|\d+)\]", repl, name)


def parse_cffdump_draw_registers(summary_path: Path, draw_index: int = 2) -> dict[str, int]:
    lines = summary_path.read_text(encoding="utf-8").splitlines()
    start_marker = f"draw[{draw_index}] register values"
    start = None
    for idx, line in enumerate(lines):
        if start_marker in line:
            start = idx + 1
            break
    if start is None:
        raise ValueError(f"{start_marker!r} not found in {summary_path}")

    regs: dict[str, int] = {}
    for line in lines[start:]:
        if re.search(r"draw\[\d+\] register values", line):
            break
        if line.startswith("cmdstream["):
            break
        match = REGISTER_LINE_RE.match(line)
        if not match:
            continue
        name = _normalize_reg_name(match.group("name"))
        regs[name] = int(match.group("value"), 16)
    if not regs:
        raise ValueError(f"no draw[{draw_index}] registers parsed from {summary_path}")
    return regs


def _vfd_fetch_instr(idx: int, byte_offset: int, fmt: int, swap: int) -> int:
    return (
        (idx & 0x1F)
        | ((byte_offset & 0xFFF) << 5)
        | ((fmt & 0xFF) << 20)
        | ((swap & 0x3) << 28)
        | (1 << 31)
    )


def _vfd_dest_instr(regid: int, writemask: int) -> int:
    return (writemask & 0xF) | ((regid & 0xFF) << 4)


def _sp_xs_cntl0(fullregfootprint: int, *flags: int) -> int:
    value = (fullregfootprint & 0x3F) << 7
    for flag in flags:
        value |= flag
    return value


def current_h3_registers(dispatch: Path = DISPATCH) -> dict[str, int]:
    source = dispatch.read_text(encoding="utf-8")
    macros = MacroResolver(source)
    m = macros.resolve

    color_mask = m("GPU_H3_COLOR_OUTPUT_MASK")
    color_format = m("GPU_H3_COLOR_FORMAT")
    color_flag_mrt = True
    rb_tile_mode = m("GPU_G4_A6XX_TILE6_3") if color_flag_mrt else m("GPU_G4_A6XX_TILE6_LINEAR")
    rb_mrt_control = (color_mask & 0xF) << 7
    rb_mrt_info = (
        color_format
        | (rb_tile_mode << 8)
        | (m("GPU_G4_A3XX_COLOR_SWAP_WZYX") << 13)
    )
    pitch_qwords = m("GPU_H2_COLOR_STRIDE") >> 6
    array_pitch_qwords = (m("GPU_H2_COLOR_STRIDE") * m("GPU_H2_COLOR_HEIGHT")) >> 6
    vertex_bytes = m("GPU_H3_VERTEX_DWORDS") * 4
    sp_vs_cntl0 = _sp_xs_cntl0(
        m("GPU_H3_SP_VS_FULLREGFOOTPRINT"),
        m("GPU_H3_SP_VS_CNTL_0_MERGEDREGS"),
        m("GPU_H3_SP_VS_CNTL_0_UNKNOWN31"),
    )
    sp_ps_cntl0 = _sp_xs_cntl0(
        m("GPU_H3_SP_PS_FULLREGFOOTPRINT"),
        m("GPU_H3_SP_PS_CNTL_0_THREADSIZE"),
        m("GPU_H3_SP_PS_CNTL_0_VARYING"),
        m("GPU_H3_SP_PS_CNTL_0_INOUTREGOVERLAP"),
        m("GPU_H3_SP_PS_CNTL_0_MERGEDREGS"),
    )

    regs = {
        "GRAS_CL_CNTL": m("GPU_H3_GRAS_CL_CNTL"),
        "GRAS_CL_VS_CLIP_CULL_DISTANCE": m("GPU_H3_GRAS_CL_VS_CLIP_CULL_DISTANCE"),
        "GRAS_CL_INTERP_CNTL": m("GPU_H3_GRAS_CL_INTERP_CNTL"),
        "GRAS_CL_GUARDBAND_CLIP_ADJ": m("GPU_H3_GRAS_CL_GUARDBAND_CLIP_ADJ"),
        "GRAS_SU_CNTL": m("GPU_H3_GRAS_SU_CNTL"),
        "GRAS_SU_POINT_MINMAX": m("GPU_H3_GRAS_SU_POINT_MINMAX"),
        "GRAS_SU_POINT_SIZE": m("GPU_H3_GRAS_SU_POINT_SIZE"),
        "GRAS_SU_POLY_OFFSET_SCALE": m("GPU_H3_GRAS_SU_POLY_OFFSET_SCALE"),
        "GRAS_SU_POLY_OFFSET_OFFSET": m("GPU_H3_GRAS_SU_POLY_OFFSET_OFFSET"),
        "GRAS_SU_POLY_OFFSET_OFFSET_CLAMP": m("GPU_H3_GRAS_SU_POLY_OFFSET_OFFSET_CLAMP"),
        "GRAS_SU_VS_SIV_CNTL": m("GPU_H3_GRAS_SU_VS_SIV_CNTL"),
        "GRAS_SC_CNTL": 2,
        "GRAS_SC_RAS_MSAA_CNTL": 0,
        "GRAS_SC_DEST_MSAA_CNTL": 1 << 2,
        "GRAS_SC_MSAA_SAMPLE_POS_CNTL": m("GPU_H3_GRAS_SC_MSAA_SAMPLE_POS_CNTL"),
        "GRAS_LRZ_CNTL": 0,
        "GRAS_LRZ_PS_INPUT_CNTL": m("GPU_H3_GRAS_LRZ_PS_INPUT_CNTL"),
        "GRAS_LRZ_PS_SAMPLEFREQ_CNTL": m("GPU_H3_GRAS_LRZ_PS_SAMPLEFREQ_CNTL"),
        "RB_RENDER_CNTL": m("GPU_H3_RB_RENDER_CNTL"),
        "RB_RAS_MSAA_CNTL": 0,
        "RB_DEST_MSAA_CNTL": 1 << 2,
        "RB_MSAA_SAMPLE_POS_CNTL": m("GPU_H3_RB_MSAA_SAMPLE_POS_CNTL"),
        "RB_INTERP_CNTL": m("GPU_H3_RB_INTERP_CNTL"),
        "RB_PS_INPUT_CNTL": m("GPU_H3_RB_PS_INPUT_CNTL"),
        "RB_PS_OUTPUT_CNTL": m("GPU_H3_RB_PS_OUTPUT_CNTL"),
        "RB_PS_MRT_CNTL": m("GPU_H3_RB_PS_MRT_CNTL"),
        "RB_PS_OUTPUT_MASK": color_mask,
        "RB_SRGB_CNTL": 0,
        "RB_PS_SAMPLEFREQ_CNTL": m("GPU_H3_RB_PS_SAMPLEFREQ_CNTL"),
        "RB_BLEND_CNTL": m("GPU_H3_RB_BLEND_CNTL"),
        "RB_DEPTH_CNTL": 0,
        "RB_STENCIL_CNTL": 0,
        "RB_MRT[0].CONTROL": rb_mrt_control,
        "RB_MRT[0].BLEND_CONTROL": m("GPU_H3_RB_MRT0_BLEND_CONTROL"),
        "RB_MRT[0].BUF_INFO": rb_mrt_info,
        "RB_MRT[0].PITCH": pitch_qwords,
        "RB_MRT[0].ARRAY_PITCH": array_pitch_qwords,
        "RB_MRT[0].BASE_GMEM": 0,
        "RB_COLOR_FLAG_BUFFER[0].PITCH": m("GPU_H3_COLOR_FLAG_BUFFER_PITCH"),
        "VPC_VS_CLIP_CULL_CNTL": m("GPU_H3_VPC_VS_CLIP_CULL_CNTL"),
        "VPC_VS_SIV_CNTL": m("GPU_H3_VPC_VS_SIV_CNTL"),
        "VPC_RAST_CNTL": m("GPU_H3_VPC_RAST_CNTL"),
        "VPC_VARYING_LM_TRANSFER_CNTL[0].DISABLE": m("GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL0"),
        "VPC_VARYING_LM_TRANSFER_CNTL[1].DISABLE": m("GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL1"),
        "VPC_VARYING_LM_TRANSFER_CNTL[2].DISABLE": m("GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL2"),
        "VPC_VARYING_LM_TRANSFER_CNTL[3].DISABLE": m("GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL3"),
        "VPC_VS_CNTL": m("GPU_H3_VPC_VS_CNTL"),
        "VPC_PS_CNTL": m("GPU_H3_VPC_PS_CNTL"),
        "VPC_SO_OVERRIDE": m("GPU_H3_VPC_SO_OVERRIDE"),
        "PC_RESTART_INDEX": 0xFFFFFFFF,
        "PC_MODE_CNTL": m("GPU_H3_PC_MODE_CNTL"),
        "VPC_RAST_STREAM_CNTL": m("GPU_H3_VPC_RAST_STREAM_CNTL"),
        "PC_DGEN_RAST_CNTL": m("GPU_H3_PC_DGEN_RAST_CNTL"),
        "PC_CNTL": 0,
        "PC_VS_CNTL": m("GPU_H3_PC_VS_CNTL"),
        "PC_STEREO_RENDERING_CNTL": m("GPU_H3_PC_STEREO_RENDERING_CNTL"),
        "VFD_CNTL_0": m("GPU_H3_VFD_CNTL_0"),
        "VFD_CNTL_1": m("GPU_H3_VFD_CNTL_1"),
        "VFD_CNTL_2": m("GPU_H3_VFD_CNTL_2"),
        "VFD_CNTL_3": m("GPU_H3_VFD_CNTL_3"),
        "VFD_CNTL_4": m("GPU_H3_VFD_CNTL_4"),
        "VFD_CNTL_5": m("GPU_H3_VFD_CNTL_5"),
        "VFD_CNTL_6": m("GPU_H3_VFD_CNTL_6"),
        "VFD_VERTEX_BUFFER[0].SIZE": vertex_bytes,
        "VFD_VERTEX_BUFFER[0].STRIDE": m("GPU_H3_VERTEX_STRIDE"),
        "VFD_FETCH_INSTR[0].INSTR": m("GPU_H3_VFD_FETCH_INSTR0"),
        "VFD_FETCH_INSTR[0].STEP_RATE": m("GPU_H3_VFD_FETCH_STEP_RATE"),
        "VFD_FETCH_INSTR[1].INSTR": m("GPU_H3_VFD_FETCH_INSTR1"),
        "VFD_FETCH_INSTR[1].STEP_RATE": m("GPU_H3_VFD_FETCH_STEP_RATE"),
        "VFD_FETCH_INSTR[2].INSTR": m("GPU_H3_VFD_FETCH_INSTR2"),
        "VFD_FETCH_INSTR[2].STEP_RATE": m("GPU_H3_VFD_FETCH_STEP_RATE"),
        "VFD_DEST_CNTL[0].INSTR": m("GPU_H3_VFD_DEST_CNTL0"),
        "VFD_DEST_CNTL[1].INSTR": m("GPU_H3_VFD_DEST_CNTL1"),
        "VFD_DEST_CNTL[2].INSTR": m("GPU_H3_VFD_DEST_CNTL2"),
        "SP_VS_CNTL_0": sp_vs_cntl0,
        "SP_VS_OUTPUT_CNTL": m("GPU_H3_SP_VS_OUTPUT_CNTL"),
        "SP_VS_OUTPUT[0].REG": m("GPU_H3_SP_VS_OUTPUT_REG0"),
        "SP_VS_VPC_DEST[0].REG": m("GPU_H3_SP_VS_VPC_DEST_REG0"),
        "SP_VS_PROGRAM_COUNTER_OFFSET": 0,
        "SP_VS_CONFIG": m("GPU_H1_SP_CONFIG_ENABLED"),
        "SP_VS_INSTR_SIZE": m("GPU_H3_VS_SHADER_INSTRLEN"),
        "SP_PS_CNTL_0": sp_ps_cntl0,
        "SP_PS_PROGRAM_COUNTER_OFFSET": 0,
        "SP_BLEND_CNTL": m("GPU_H3_SP_BLEND_CNTL"),
        "SP_SRGB_CNTL": 0,
        "SP_PS_OUTPUT_MASK": color_mask,
        "SP_PS_OUTPUT_CNTL": m("GPU_H3_SP_PS_OUTPUT_CNTL"),
        "SP_PS_MRT_CNTL": m("GPU_H3_SP_PS_MRT_CNTL"),
        "SP_PS_OUTPUT[0].REG": m("GPU_H3_PS_OUTPUT_REGID"),
        "SP_PS_MRT[0].REG": m("GPU_H3_SP_PS_MRT_REG0"),
        "SP_PS_INITIAL_TEX_LOAD_CNTL": m("GPU_H3_SP_PS_INITIAL_TEX_LOAD_CNTL"),
        "SP_MODE_CNTL": m("GPU_H3_SP_MODE_CNTL"),
        "SP_PS_CONFIG": m("GPU_H1_SP_CONFIG_ENABLED"),
        "SP_PS_INSTR_SIZE": m("GPU_H3_FS_SHADER_INSTRLEN"),
        "SP_VS_CONST_CONFIG": m("GPU_H3_SP_CONST_CONFIG_ENABLED"),
        "SP_PS_CONST_CONFIG": m("GPU_H3_SP_CONST_CONFIG_ENABLED"),
        "SP_PS_WAVE_CNTL": m("GPU_H3_SP_PS_WAVE_CNTL"),
        "SP_LB_PARAM_LIMIT": m("GPU_H3_SP_LB_PARAM_LIMIT"),
        "SP_REG_PROG_ID_0": m("GPU_H3_SP_REG_PROG_ID_0"),
        "SP_REG_PROG_ID_1": m("GPU_H3_SP_REG_PROG_ID_1"),
        "SP_REG_PROG_ID_2": m("GPU_H3_SP_REG_PROG_ID_2"),
        "SP_REG_PROG_ID_3": m("GPU_H3_SP_REG_PROG_ID_3"),
        "SP_UPDATE_CNTL": m("GPU_H3_SP_UPDATE_CNTL_DRAW_STATE"),
    }
    invalid = m("GPU_H3_SP_INVALID_REG")
    for index in range(1, 8):
        regs[f"SP_PS_OUTPUT[{index}].REG"] = invalid
    return regs


def _comparison(ref: dict[str, int], cur: dict[str, int], keys: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in keys:
        ref_value = ref.get(key)
        cur_value = cur.get(key)
        rows.append(
            {
                "register": key,
                "reference": ref_value,
                "current_h3": cur_value,
                "matches": ref_value is not None and cur_value is not None and ref_value == cur_value,
            }
        )
    return rows


def run_diff(
    summary_path: Path = DEFAULT_SUMMARY,
    rd_path: Path = DEFAULT_RD,
    dispatch: Path = DISPATCH,
    draw_index: int = 2,
) -> dict[str, Any]:
    ref = parse_cffdump_draw_registers(summary_path, draw_index=draw_index)
    cur = current_h3_registers(dispatch)

    core_keys = [
        "GRAS_CL_CNTL",
        "GRAS_CL_INTERP_CNTL",
        "GRAS_CL_GUARDBAND_CLIP_ADJ",
        "GRAS_SU_CNTL",
        "GRAS_SC_CNTL",
        "GRAS_SC_DEST_MSAA_CNTL",
        "GRAS_LRZ_CNTL",
        "RB_RENDER_CNTL",
        "RB_DEST_MSAA_CNTL",
        "RB_INTERP_CNTL",
        "RB_PS_OUTPUT_CNTL",
        "RB_PS_MRT_CNTL",
        "RB_PS_OUTPUT_MASK",
        "RB_MRT[0].CONTROL",
        "RB_MRT[0].BUF_INFO",
        "RB_MRT[0].BASE_GMEM",
        "RB_COLOR_FLAG_BUFFER[0].PITCH",
        "VPC_VS_CLIP_CULL_CNTL",
        "VPC_VS_SIV_CNTL",
        "VPC_RAST_CNTL",
        "VPC_VS_CNTL",
        "VPC_PS_CNTL",
        "VPC_SO_OVERRIDE",
        "PC_RESTART_INDEX",
        "PC_MODE_CNTL",
        "VPC_RAST_STREAM_CNTL",
        "PC_DGEN_RAST_CNTL",
        "PC_CNTL",
        "PC_VS_CNTL",
        "SP_VS_CNTL_0",
        "SP_VS_OUTPUT_CNTL",
        "SP_VS_OUTPUT[0].REG",
        "SP_VS_VPC_DEST[0].REG",
        "SP_VS_CONFIG",
        "SP_VS_INSTR_SIZE",
        "SP_PS_CNTL_0",
        "SP_PS_OUTPUT_MASK",
        "SP_PS_OUTPUT_CNTL",
        "SP_PS_MRT_CNTL",
        "SP_PS_OUTPUT[0].REG",
        "SP_PS_MRT[0].REG",
        "SP_PS_INITIAL_TEX_LOAD_CNTL",
        "SP_MODE_CNTL",
        "SP_PS_CONFIG",
        "SP_PS_INSTR_SIZE",
        "SP_PS_CONST_CONFIG",
        "SP_PS_WAVE_CNTL",
        "SP_LB_PARAM_LIMIT",
        "SP_REG_PROG_ID_0",
        "SP_REG_PROG_ID_1",
        "SP_REG_PROG_ID_2",
        "SP_UPDATE_CNTL",
    ]
    compare_rows = _comparison(ref, cur, core_keys)
    matched_core = [row for row in compare_rows if row["matches"]]
    mismatched_core = [row for row in compare_rows if not row["matches"]]

    candidates = [
        {
            "name": "vfd_fetch_decode_shader_contract",
            "priority": 1,
            "classification": "structural_shader_vfd_coupled",
            "reference": {
                "VFD_CNTL_0": ref.get("VFD_CNTL_0"),
                "VFD_CNTL_1": ref.get("VFD_CNTL_1"),
                "VFD_VERTEX_BUFFER[0].STRIDE": ref.get("VFD_VERTEX_BUFFER[0].STRIDE"),
                "VFD_FETCH_INSTR[0].INSTR": ref.get("VFD_FETCH_INSTR[0].INSTR"),
                "VFD_FETCH_INSTR[1].INSTR": ref.get("VFD_FETCH_INSTR[1].INSTR"),
                "VFD_FETCH_INSTR[2].INSTR": ref.get("VFD_FETCH_INSTR[2].INSTR"),
                "VFD_DEST_CNTL[0].INSTR": ref.get("VFD_DEST_CNTL[0].INSTR"),
                "VFD_DEST_CNTL[1].INSTR": ref.get("VFD_DEST_CNTL[1].INSTR"),
                "VFD_DEST_CNTL[2].INSTR": ref.get("VFD_DEST_CNTL[2].INSTR"),
            },
            "current_h3": {
                "VFD_CNTL_0": cur.get("VFD_CNTL_0"),
                "VFD_CNTL_1": cur.get("VFD_CNTL_1"),
                "VFD_VERTEX_BUFFER[0].STRIDE": cur.get("VFD_VERTEX_BUFFER[0].STRIDE"),
                "VFD_FETCH_INSTR[0].INSTR": cur.get("VFD_FETCH_INSTR[0].INSTR"),
                "VFD_FETCH_INSTR[1].INSTR": cur.get("VFD_FETCH_INSTR[1].INSTR"),
                "VFD_FETCH_INSTR[2].INSTR": cur.get("VFD_FETCH_INSTR[2].INSTR"),
                "VFD_DEST_CNTL[0].INSTR": cur.get("VFD_DEST_CNTL[0].INSTR"),
                "VFD_DEST_CNTL[1].INSTR": cur.get("VFD_DEST_CNTL[1].INSTR"),
                "VFD_DEST_CNTL[2].INSTR": cur.get("VFD_DEST_CNTL[2].INSTR"),
            },
            "next_unit_guidance": (
                "Do not single-register copy. A bounded live unit would replace the H3 "
                "vertex payload, VFD fetch/decode, and VS input contract coherently."
            ),
        },
        {
            "name": "sp_rb_blend_output_state_group",
            "priority": 2,
            "classification": "direct_sysmem_compatible_output_state",
            "reference": {
                "SP_BLEND_CNTL": ref.get("SP_BLEND_CNTL"),
                "RB_BLEND_CNTL": ref.get("RB_BLEND_CNTL"),
                "RB_MRT[0].BLEND_CONTROL": ref.get("RB_MRT[0].BLEND_CONTROL"),
            },
            "current_h3": {
                "SP_BLEND_CNTL": cur.get("SP_BLEND_CNTL"),
                "RB_BLEND_CNTL": cur.get("RB_BLEND_CNTL"),
                "RB_MRT[0].BLEND_CONTROL": cur.get("RB_MRT[0].BLEND_CONTROL"),
            },
            "next_unit_guidance": (
                "This is the smallest remaining direct-sysmem-safe output-state group, "
                "although blending is disabled in the reference draw."
            ),
        },
        {
            "name": "sp_vs_const_config_shader_contract",
            "priority": 3,
            "classification": "shader_constant_contract_coupled",
            "reference": {"SP_VS_CONST_CONFIG": ref.get("SP_VS_CONST_CONFIG")},
            "current_h3": {"SP_VS_CONST_CONFIG": cur.get("SP_VS_CONST_CONFIG")},
            "next_unit_guidance": (
                "Reference VS uses c1 constants; current H3 VS does not. Treat as part "
                "of a reference VS/VFD contract replay, not an isolated fix."
            ),
        },
        {
            "name": "sp_reg_prog_id_3_foveation_quality",
            "priority": 4,
            "classification": "low_priority_frontend_sysval_delta",
            "reference": {"SP_REG_PROG_ID_3": ref.get("SP_REG_PROG_ID_3")},
            "current_h3": {"SP_REG_PROG_ID_3": cur.get("SP_REG_PROG_ID_3")},
            "next_unit_guidance": (
                "Track as a real diff but keep behind VFD/VS contract and blend-output "
                "groups unless later cffdump evidence raises it."
            ),
        },
    ]

    excluded = [
        {
            "name": "target_size_dependent_surface_values",
            "registers": [
                "GRAS_CL_VIEWPORT[0].XOFFSET",
                "GRAS_CL_VIEWPORT[0].XSCALE",
                "GRAS_SC_SCREEN_SCISSOR[0].BR",
                "RB_MRT[0].PITCH",
                "RB_MRT[0].ARRAY_PITCH",
            ],
            "reason": "reference draw is 256x256; H3 target is 128x128",
        },
        {
            "name": "gmem_vs_direct_sysmem_path_values",
            "registers": [
                "RB_CCU_CNTL",
                "GRAS_SC_BIN_CNTL",
                "RB_CNTL",
            ],
            "reason": "reference draw[2] is the GMEM draw pass; H3 intentionally uses direct sysmem",
        },
        {
            "name": "addresses",
            "registers": [
                "SP_VS_BASE",
                "SP_PS_BASE",
                "VFD_VERTEX_BUFFER[0].BASE",
                "RB_MRT[0].BASE",
                "RB_COLOR_FLAG_BUFFER[0].ADDR",
            ],
            "reason": "addresses are allocation-instance dependent",
        },
    ]

    return {
        "cycle": CYCLE,
        "scope": SCOPE,
        "passed": True,
        "draw_index": draw_index,
        "summary_path": str(summary_path),
        "rd_path": str(rd_path) if rd_path else None,
        "rd_sha256": _sha256(rd_path) if rd_path else None,
        "dispatch": str(dispatch.relative_to(REPO_ROOT)) if dispatch.is_relative_to(REPO_ROOT) else str(dispatch),
        "checks": {
            "cffdump_summary_exists": summary_path.is_file(),
            "rd_exists": rd_path.is_file() if rd_path else False,
            "draw_registers_parsed": len(ref),
            "current_h3_registers_resolved": len(cur),
            "no_device_flash_required": True,
            "matched_core_count": len(matched_core),
            "mismatched_core_count": len(mismatched_core),
            "top_candidate_count": len(candidates),
            "candidate_delta_count": sum(
                1
                for candidate in candidates
                if candidate["reference"] != candidate["current_h3"]
            ),
        },
        "matched_core": matched_core,
        "mismatched_core": mismatched_core,
        "top_candidates": candidates,
        "excluded_or_contextual_differences": excluded,
        "notes": [
            "The local cffdump draw[2] is a real A640 triangle draw, but it is a GMEM pass with a later resolve.",
            "Only direct-sysmem-compatible deltas should become H3 live probes.",
            "This unit is host-only and intentionally does not build or flash a boot image.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--rd", type=Path, default=DEFAULT_RD)
    parser.add_argument("--dispatch", type=Path, default=DISPATCH)
    parser.add_argument("--draw-index", type=int, default=2)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    result = run_diff(
        summary_path=args.summary,
        rd_path=args.rd,
        dispatch=args.dispatch,
        draw_index=args.draw_index,
    )
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
