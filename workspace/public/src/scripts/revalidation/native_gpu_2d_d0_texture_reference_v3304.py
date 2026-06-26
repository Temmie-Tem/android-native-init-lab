#!/usr/bin/env python3
"""Validate the staged A640 texture/blit reference for the D0 rung."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root


CYCLE = "V3304"
SCOPE = "gpu-2d-d0-texture-reference-recon"
REPO_ROOT = repo_root()
STAGED_ROOT = Path("/tmp/a90-mesa-gpu-src")

REFERENCE = STAGED_ROOT / "a6xx_texture_blit_reference_v3304.txt"
FD6_TEXTURE_CC = STAGED_ROOT / "src/gallium/drivers/freedreno/a6xx/fd6_texture.cc"
FD6_TEXTURE_H = STAGED_ROOT / "src/gallium/drivers/freedreno/a6xx/fd6_texture.h"
FD6_EMIT_CC = STAGED_ROOT / "src/gallium/drivers/freedreno/a6xx/fd6_emit.cc"
FD6_EMIT_H = STAGED_ROOT / "src/gallium/drivers/freedreno/a6xx/fd6_emit.h"
FD6_PROGRAM_CC = STAGED_ROOT / "src/gallium/drivers/freedreno/a6xx/fd6_program.cc"
A6XX_XML = STAGED_ROOT / "src/freedreno/registers/adreno/a6xx.xml"
PM4_XML = STAGED_ROOT / "src/freedreno/registers/adreno/adreno_pm4.xml"
IR3_CAT5_XML = STAGED_ROOT / "src/freedreno/isa/ir3-cat5.xml"

MESA_COMMIT = "6adb0d5e01dca952fcb04b7773ad92b0ab2e132d"

EXPECTED_REG_OFFSETS = {
    "SP_PS_CONFIG": 0xAB04,
    "SP_PS_INSTR_SIZE": 0xAB05,
    "SP_PS_INITIAL_TEX_LOAD_CNTL": 0xA99E,
    "SP_PS_INITIAL_TEX_LOAD": 0xA99F,
    "SP_PS_INITIAL_TEX_INDEX": 0xA9A3,
    "SP_PS_TSIZE": 0xA9A7,
    "SP_PS_SAMPLER_BASE": 0xA9E0,
    "SP_PS_TEXMEMOBJ_BASE": 0xA9E4,
    "SP_UPDATE_CNTL": 0xBB08,
    "TPL1_GFX_BORDER_COLOR_BASE": 0xB302,
    "TPL1_MSAA_SAMPLE_POS_CNTL": 0xB304,
    "TPL1_WINDOW_OFFSET": 0xB307,
    "TPL1_MODE_CNTL": 0xB309,
}

EXPECTED_PM4_VALUES = {
    "CP_LOAD_STATE6_FRAG": 0x34,
    "CP_SET_DRAW_STATE": 0x43,
    "CP_DRAW_INDX_OFFSET": 0x38,
    "CP_WAIT_FOR_IDLE": 0x26,
    "SB6_FS_TEX": 0x04,
    "SB6_FS_SHADER": 0x0C,
    "ST6_SHADER": 0x00,
    "ST6_CONSTANTS": 0x01,
    "SS6_INDIRECT": 0x02,
}

REFERENCE_MARKERS = [
    "V3304 A640 texture/blit reference summary",
    "fd6_texture.cc",
    "fd6_emit.cc",
    "fd6_program.cc",
    "state_type=ST6_SHADER",
    "state_type=ST6_CONSTANTS",
    "state_block=SB6_FS_TEX",
    "s#0/t#0",
    "D1 target",
]

TEXTURE_SOURCE_MARKERS = [
    "tex->num_samplers * 4 * 4",
    "memcpy(buf, sampler->descriptor, 4 * 4)",
    "tex->num_textures * 16 * 4",
    "memcpy(buf, view->descriptor, 16 * 4)",
    "A6XX_SP_PS_SAMPLER_BASE(samp_desc)",
    "A6XX_SP_PS_TEXMEMOBJ_BASE(tex_desc)",
    "A6XX_SP_PS_TSIZE(tex->num_textures)",
    ".state_type = ST6_SHADER",
    ".state_type = ST6_CONSTANTS",
    ".state_src = SS6_INDIRECT",
    ".state_block = stage2sb(type)",
    "case MESA_SHADER_FRAGMENT:   return SB6_FS_TEX;",
]

TEXTURE_HEADER_MARKERS = [
    "uint32_t descriptor[4];",
    "uint32_t descriptor[FDL6_TEX_CONST_DWORDS];",
    ".tile_mode = TILE6_LINEAR",
]

EMIT_SOURCE_MARKERS = [
    "case FD6_GROUP_FS_TEX:",
    "tex_state<CHIP>(ctx, MESA_SHADER_FRAGMENT)",
    "fd6_state_take_group(&emit->state, state, FD6_GROUP_FS_TEX)",
    "fd6_state_emit(&emit->state, cs)",
]

PROGRAM_SOURCE_MARKERS = [
    "A6XX_SP_PS_CONFIG(.dword = sp_xs_config(state->fs))",
    "A6XX_SP_VS_CONFIG_NTEX(v->num_samp)",
    "A6XX_SP_VS_CONFIG_NSAMP(v->num_samp)",
    "SP_UPDATE_CNTL(CHIP,",
    ".fs_state = true",
    "A6XX_SP_PS_INITIAL_TEX_LOAD_CNTL",
    "SP_PS_INITIAL_TEX_LOAD_CMD",
]

EMIT_HEADER_MARKERS = [
    "return fd6_geom_stage(type) ? CP_LOAD_STATE6_GEOM : CP_LOAD_STATE6_FRAG;",
    "case MESA_SHADER_FRAGMENT:",
    "return SB6_FS_SHADER;",
]

ORDERED_ENVELOPE = [
    {
        "stage": "reuse_h_triangle_draw_baseline",
        "source": "H0-H5 VS/raster/RB/sysmem/KMS path stays closed and reused",
    },
    {
        "stage": "fs_program_config",
        "registers": ["SP_UPDATE_CNTL", "SP_PS_CONFIG", "SP_PS_INSTR_SIZE"],
        "requirements": ["FS_STATE update", "NTEX=1", "NSAMP=1", "FS shader preload"],
    },
    {
        "stage": "fs_texture_state_group",
        "draw_state_group": "FD6_GROUP_FS_TEX",
        "producer": "fd6_texture_state(ctx, MESA_SHADER_FRAGMENT)",
    },
    {
        "stage": "fs_sampler_descriptor",
        "descriptor_dwords": 4,
        "registers": ["SP_PS_SAMPLER_BASE"],
        "packet": "CP_LOAD_STATE6_FRAG",
        "state_type": "ST6_SHADER",
        "state_src": "SS6_INDIRECT",
        "state_block": "SB6_FS_TEX",
    },
    {
        "stage": "fs_texture_descriptor",
        "descriptor_dwords": 16,
        "registers": ["SP_PS_TEXMEMOBJ_BASE", "SP_PS_TSIZE"],
        "packet": "CP_LOAD_STATE6_FRAG",
        "state_type": "ST6_CONSTANTS",
        "state_src": "SS6_INDIRECT",
        "state_block": "SB6_FS_TEX",
    },
    {
        "stage": "tpl1_draw_baseline",
        "registers": ["TPL1_MODE_CNTL", "TPL1_GFX_BORDER_COLOR_BASE", "TPL1_WINDOW_OFFSET"],
    },
    {
        "stage": "textured_fs_shader_contract",
        "ir3_op": "sam",
        "binding_model": "CAT5_UNIFORM",
        "sampler": "s#0",
        "texture": "t#0",
        "note": "shader bytes still require ir3-disasm verification before D1 flash",
    },
    {
        "stage": "d1_static_checkerboard_target",
        "pass_criterion": "readback contains sampled checkerboard pattern, not clear color",
    },
]


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_int(raw: str) -> int:
    return int(raw, 0)


def _variant_matches_a6xx(variants: str | None) -> bool:
    if variants is None:
        return True
    return variants in {"A6XX", "A6XX-", "A6XX-A7XX"}


def _local_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _parse_a6xx_offsets(xml_path: Path = A6XX_XML) -> dict[str, int]:
    root = ET.parse(xml_path).getroot()
    offsets: dict[str, int] = {}
    for element in root.iter():
        tag = _local_tag(element)
        if tag not in {"reg32", "reg64", "array"}:
            continue
        name = element.attrib.get("name")
        if name not in EXPECTED_REG_OFFSETS:
            continue
        if not _variant_matches_a6xx(element.attrib.get("variants")):
            continue
        offsets.setdefault(name, _parse_int(element.attrib["offset"]))
    return offsets


def _parse_pm4_values(xml_path: Path = PM4_XML) -> dict[str, int]:
    root = ET.parse(xml_path).getroot()
    values: dict[str, int] = {}
    for element in root.iter():
        if _local_tag(element) != "value":
            continue
        name = element.attrib.get("name")
        if name in EXPECTED_PM4_VALUES:
            values.setdefault(name, _parse_int(element.attrib["value"]))
    return values


def _source_contains_all(path: Path, markers: list[str]) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8")
    return {marker: marker in text for marker in markers}


def _parse_cat5_sam_contract(xml_path: Path = IR3_CAT5_XML) -> dict[str, Any]:
    text = xml_path.read_text(encoding="utf-8")
    sam_match = re.search(r'<bitset name="sam"[\s\S]*?</bitset>', text)
    instruction_match = re.search(r'<bitset name="#instruction-cat5"[\s\S]*?</bitset>', text)
    uniform_match = re.search(r'<value val="0" display="CAT5_UNIFORM"[\s\S]*?</value>', text)
    sam_block = sam_match.group(0) if sam_match else ""
    instruction_block = instruction_match.group(0) if instruction_match else ""
    uniform_block = uniform_match.group(0) if uniform_match else ""
    return {
        "path": str(xml_path),
        "has_sam_bitset": bool(sam_block),
        "sam_has_sampler": 'HAS_SAMP" expr="#true"' in sam_block,
        "sam_has_texture": 'HAS_TEX" expr="#true"' in sam_block,
        "sam_has_type": 'HAS_TYPE" expr="#true"' in sam_block,
        "sam_pattern": "00011" if "00011" in sam_block else None,
        "instruction_has_samp_field": 'name="SAMP" low="21" high="24"' in instruction_block,
        "instruction_has_tex_field": 'name="TEX" low="25" high="31"' in instruction_block,
        "non_bindless_uniform_mode": "Use traditional GL binding model" in uniform_block,
        "non_bindless_uniform_from_src3": "from src3" in uniform_block,
        "valid": all(
            [
                bool(sam_block),
                'HAS_SAMP" expr="#true"' in sam_block,
                'HAS_TEX" expr="#true"' in sam_block,
                'HAS_TYPE" expr="#true"' in sam_block,
                'name="SAMP" low="21" high="24"' in instruction_block,
                'name="TEX" low="25" high="31"' in instruction_block,
                "Use traditional GL binding model" in uniform_block,
                "from src3" in uniform_block,
            ]
        ),
    }


def run_recon(staged_root: Path = STAGED_ROOT) -> dict[str, Any]:
    files = {
        "reference": staged_root / REFERENCE.relative_to(STAGED_ROOT),
        "fd6_texture_cc": staged_root / FD6_TEXTURE_CC.relative_to(STAGED_ROOT),
        "fd6_texture_h": staged_root / FD6_TEXTURE_H.relative_to(STAGED_ROOT),
        "fd6_emit_cc": staged_root / FD6_EMIT_CC.relative_to(STAGED_ROOT),
        "fd6_emit_h": staged_root / FD6_EMIT_H.relative_to(STAGED_ROOT),
        "fd6_program_cc": staged_root / FD6_PROGRAM_CC.relative_to(STAGED_ROOT),
        "a6xx_xml": staged_root / A6XX_XML.relative_to(STAGED_ROOT),
        "pm4_xml": staged_root / PM4_XML.relative_to(STAGED_ROOT),
        "ir3_cat5_xml": staged_root / IR3_CAT5_XML.relative_to(STAGED_ROOT),
    }
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        return {
            "cycle": CYCLE,
            "scope": SCOPE,
            "passed": False,
            "missing_files": missing,
            "files": {name: str(path) for name, path in files.items()},
        }

    offsets = _parse_a6xx_offsets(files["a6xx_xml"])
    pm4_values = _parse_pm4_values(files["pm4_xml"])
    cat5_contract = _parse_cat5_sam_contract(files["ir3_cat5_xml"])

    offset_mismatches = {
        name: {"expected": expected, "actual": offsets.get(name)}
        for name, expected in EXPECTED_REG_OFFSETS.items()
        if offsets.get(name) != expected
    }
    pm4_mismatches = {
        name: {"expected": expected, "actual": pm4_values.get(name)}
        for name, expected in EXPECTED_PM4_VALUES.items()
        if pm4_values.get(name) != expected
    }

    reference_markers = _source_contains_all(files["reference"], REFERENCE_MARKERS)
    texture_markers = _source_contains_all(files["fd6_texture_cc"], TEXTURE_SOURCE_MARKERS)
    texture_header_markers = _source_contains_all(files["fd6_texture_h"], TEXTURE_HEADER_MARKERS)
    emit_markers = _source_contains_all(files["fd6_emit_cc"], EMIT_SOURCE_MARKERS)
    emit_header_markers = _source_contains_all(files["fd6_emit_h"], EMIT_HEADER_MARKERS)
    program_markers = _source_contains_all(files["fd6_program_cc"], PROGRAM_SOURCE_MARKERS)

    checks = {
        "reference_files_present": not missing,
        "reference_summary_present": all(reference_markers.values()),
        "texture_descriptor_emit_confirmed": all(texture_markers.values()),
        "texture_descriptor_layout_confirmed": all(texture_header_markers.values()),
        "fs_texture_state_group_confirmed": all(emit_markers.values()),
        "fs_stage_opcode_confirmed": all(emit_header_markers.values()),
        "fs_program_config_confirmed": all(program_markers.values()),
        "xml_offsets_match_expected": not offset_mismatches,
        "pm4_values_match_expected": not pm4_mismatches,
        "cat5_sam_contract_valid": cat5_contract["valid"],
    }
    checks["d0_texture_reference_recon_passed"] = all(checks.values())

    return {
        "cycle": CYCLE,
        "scope": SCOPE,
        "mesa": {
            "root": str(staged_root),
            "commit": MESA_COMMIT,
            "source": "https://gitlab.freedesktop.org/mesa/mesa.git",
        },
        "passed": checks["d0_texture_reference_recon_passed"],
        "checks": checks,
        "files": {
            name: {"path": str(path), "sha256": _sha256(path)}
            for name, path in files.items()
        },
        "expected_reg_offsets": EXPECTED_REG_OFFSETS,
        "actual_reg_offsets": offsets,
        "offset_mismatches": offset_mismatches,
        "expected_pm4_values": EXPECTED_PM4_VALUES,
        "actual_pm4_values": pm4_values,
        "pm4_mismatches": pm4_mismatches,
        "ordered_envelope": ORDERED_ENVELOPE,
        "reference_markers": reference_markers,
        "texture_markers": texture_markers,
        "texture_header_markers": texture_header_markers,
        "emit_markers": emit_markers,
        "emit_header_markers": emit_header_markers,
        "program_markers": program_markers,
        "cat5_sam_contract": cat5_contract,
        "d1_gate": {
            "shader_bytes_verified": False,
            "ready_for_d1_live": False,
            "next_required": [
                "materialize a minimal textured FS that samples s#0/t#0 from interpolated UVs",
                "verify the generated FD640 shader words with ir3-disasm",
                "then wire the shader bytes plus the static checkerboard texture into the V3305 D1 boot artifact",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print compact JSON")
    args = parser.parse_args()
    result = run_recon()
    print(json.dumps(result, indent=None if args.json else 2, sort_keys=True))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
