from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3251_gpu_h3_compiler_vs_instrlen_probe.py"
)


class NativeGpuH3CompilerVsInstrlenSourceV3251Tests(unittest.TestCase):
    def test_v3251_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3251")
        self.assertEqual(runner.INIT_VERSION, "0.11.52")
        self.assertEqual(runner.INIT_BUILD, "v3251-gpu-h3-compiler-vs-instrlen-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3249_gpu_h3_cache_invalidate_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.52", required)
        self.assertIn(b"v3251-gpu-h3-compiler-vs-instrlen-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_payload=mesa-reference-ir3-minimal-vs-u32-z-w-instrlen1-plus-audited-fs-f32-r0x",
            required,
        )
        self.assertIn(b"gpu.h3.draw.vs_shader_instrlen=%u", required)
        self.assertIn(b"gpu.h3.draw.fs_shader_instrlen=%u", required)
        self.assertIn(b"gpu.h3.draw.ir3_mov_u32u32_r0z_hi=0x%x", required)
        self.assertNotIn(b"v3249-gpu-h3-cache-invalidate-probe", required)

    def test_dispatch_uses_compiler_reference_vs_and_instrlen_units(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H3_IR3_MOV_U32U32_R0Z_HI 0x204cc002U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_U32U32_R0W_HI 0x204cc003U", source)
        self.assertIn("#define GPU_H3_IR3_INSTR_ALIGN 16U", source)
        self.assertIn("#define GPU_H3_VS_SHADER_INSTR_COUNT 3U", source)
        self.assertIn("#define GPU_H3_FS_SHADER_INSTR_COUNT 2U", source)
        self.assertIn("#define GPU_H3_VS_SHADER_INSTRLEN 1U", source)
        self.assertIn("#define GPU_H3_FS_SHADER_INSTRLEN 1U", source)
        self.assertIn("#define GPU_H3_VS_SHADER_DWORDS GPU_H3_SHADER_ALIGNED_DWORDS", source)
        self.assertIn("#define GPU_H3_FS_SHADER_DWORDS GPU_H3_SHADER_ALIGNED_DWORDS", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_U32U32_R0Z_HI", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_U32U32_R0W_HI", source)
        self.assertNotIn("GPU_H3_IR3_F32_0_LO, GPU_H3_IR3_MOV_F32F32_R0Z_HI", source)
        self.assertIn(
            "GPU_H1_REG_SP_VS_INSTR_SIZE,\n                              GPU_H3_VS_SHADER_INSTRLEN",
            source,
        )
        self.assertIn(
            "GPU_H1_REG_SP_PS_INSTR_SIZE,\n                              GPU_H3_FS_SHADER_INSTRLEN",
            source,
        )
        self.assertIn("gpu_h3_pm4_emit_load_state6_shader_units", source)
        self.assertIn("GPU_H3_VS_SHADER_INSTRLEN) &&", source)
        self.assertIn("GPU_H3_FS_SHADER_INSTRLEN);", source)
        self.assertIn(
            '"gpu.h3.draw.scope=first-triangle-h3-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader',
            source,
        )
        self.assertIn('"gpu.h3.draw.shader_payload=mesa-reference-ir3-minimal-vs-u32-z-w-instrlen1-plus-audited-fs-f32-r0x', source)
        self.assertIn('"gpu.h3.draw.vs_shader_instrlen=%u', source)
        self.assertIn('"gpu.h3.draw.ir3_mov_u32u32_r0z_hi=0x%x', source)

    def test_builder_manifest_records_shader_load_contract(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3249-cache-invalidate-plus-v3250-live-validation-and-v3246-ir3-disasm-audit"',
            source,
        )
        self.assertIn(
            '"shader_load_contract_source": "Mesa ir3_collect_info instrlen=ceil(instr_count/16), fd6_program SP_xS_INSTR_SIZE(instrlen), CP_LOAD_STATE6 shader NUM_UNIT=1"',
            source,
        )
        self.assertIn('"vs_shader_instrlen": 1', source)
        self.assertIn('"fs_shader_instrlen": 1', source)
        self.assertIn('"vs_shader_dwords": 32', source)
        self.assertIn('"fs_shader_dwords": 32', source)
        self.assertIn("preserve-v3249-ramdisk-overlay-v3251-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3249"', source)
        self.assertIn("V3251 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
