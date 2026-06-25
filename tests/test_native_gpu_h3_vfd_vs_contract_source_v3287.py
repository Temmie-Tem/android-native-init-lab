from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3287_gpu_h3_vfd_vs_contract_probe.py"
)
audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)
diff = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_cffdump_diff_v3286.py"
)


class NativeGpuH3VfdVsContractSourceV3287Tests(unittest.TestCase):
    def test_v3287_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3287")
        self.assertEqual(runner.INIT_VERSION, "0.11.69")
        self.assertEqual(runner.INIT_BUILD, "v3287-gpu-h3-vfd-vs-contract-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3287_gpu_h3_vfd_vs_contract_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.69", required)
        self.assertIn(b"v3287-gpu-h3-vfd-vs-contract-probe", required)
        self.assertIn(b"gpu.h3.draw.vfd_contract_source=mesa-freedreno-a640-cffdump-draw2-vfd-fetch-decode-shape", required)
        self.assertIn(b"gpu.h3.draw.shader_payload=verified-ir3-vs-r1xyzw-to-r2-position-preserve-r0-varying-and-cffdump-bary-fs", required)
        self.assertIn(b"gpu.h3.draw.vfd_cntl_0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vfd_fetch_instr0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vfd_dest_cntl2=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_vs_const_config_reference_deferred=0x101-requires-vs-constant-buffer", required)

    def test_dispatch_replays_cffdump_shaped_vfd_and_constant_free_vs(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        child = source[source.index("static int gpu_h3_draw_envelope_probe_child"):]
        draw = source[source.index("static bool gpu_h3_build_draw_envelope_pm4"):]

        self.assertIn("#define GPU_H3_VERTEX_STRIDE 36U", source)
        self.assertIn("#define GPU_H3_VERTEX_DWORDS (GPU_H3_VERTEX_COUNT * 9U)", source)
        self.assertIn("#define GPU_H3_VS_SHADER_INSTR_COUNT 5U", source)
        self.assertIn("#define GPU_H3_A6XX_FMT6_32_32_32_32_FLOAT 0x82U", source)
        self.assertIn("#define GPU_H3_A6XX_FMT6_32_SINT 0x4cU", source)
        self.assertIn("#define GPU_H3_VFD_CNTL_0 0x00000303U", source)
        self.assertIn("#define GPU_H3_VFD_CNTL_1 0xfcfcfc09U", source)
        self.assertIn("#define GPU_H3_VFD_FETCH_INSTR0 0xc8200000U", source)
        self.assertIn("#define GPU_H3_VFD_FETCH_INSTR1 0xc8200200U", source)
        self.assertIn("#define GPU_H3_VFD_FETCH_INSTR2 0x44c00400U", source)
        self.assertIn("#define GPU_H3_VFD_DEST_CNTL0 0x0000000fU", source)
        self.assertIn("#define GPU_H3_VFD_DEST_CNTL1 0x0000004fU", source)
        self.assertIn("#define GPU_H3_VFD_DEST_CNTL2 0x00000081U", source)

        self.assertIn("GPU_H3_IR3_MOV_F32F32_R2X_R1X_LO", child)
        self.assertIn("GPU_H3_IR3_MOV_F32F32_R2Y_R1Y_LO", child)
        self.assertIn("GPU_H3_IR3_MOV_F32F32_R2Z_R1Z_LO", child)
        self.assertIn("GPU_H3_IR3_MOV_F32F32_R2W_R1W_LO", child)
        self.assertNotIn("GPU_H3_IR3_MOV_U32U32_R2Z_HI", child.split("static const uint32_t fs_shader", 1)[0])

        self.assertIn("GPU_H2_REG_VFD_CNTL_0,\n                              GPU_H3_VFD_CNTL_0", draw)
        self.assertIn("GPU_H3_VFD_FETCH_INSTR0", draw)
        self.assertIn("GPU_H3_VFD_FETCH_INSTR1", draw)
        self.assertIn("GPU_H3_VFD_FETCH_INSTR2", draw)
        self.assertIn("GPU_H3_VFD_DEST_CNTL0", draw)
        self.assertIn("GPU_H3_VFD_DEST_CNTL1", draw)
        self.assertIn("GPU_H3_VFD_DEST_CNTL2", draw)
        self.assertIn("*vfd_reg_writes = 20;", draw)
        self.assertIn("gpu.h3.draw.vertex_format=cffdump-shaped-r0-vec4-r1-vec4-r2x-sint", source)

    def test_shader_audit_tracks_v3287_vfd_vs_contract(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(result["passed"])
        self.assertIn(result["cycle"], {"V3287", "V3289"})
        self.assertIn(result["scope"], {
            "gpu-h3-vfd-vs-contract-replay-shader-byte-audit",
            "gpu-h3-blend-output-state-shader-byte-audit",
        })
        self.assertEqual([entry["disasm"] for entry in result["decoded"]["vs_shader"][:5]], [
            "mov.f32f32 r2.x, r1.x",
            "mov.f32f32 r2.y, r1.y",
            "mov.f32f32 r2.z, r1.z",
            "mov.f32f32 r2.w, r1.w",
            "end",
        ])
        self.assertEqual(checks["vs_shader_instrlen"], 1)
        self.assertEqual(checks["vs_position_source_regid"], 4)
        self.assertEqual(checks["vertex_stride"], 36)
        self.assertEqual(checks["vertex_dwords"], 27)
        self.assertEqual(checks["vertex_bytes"], 108)
        self.assertEqual(checks["vfd_cntl_0"], 0x303)
        self.assertEqual(checks["vfd_cntl_1"], 0xFCFCFC09)
        self.assertTrue(checks["vfd_contract_matches_a640_cffdump_draw2"])

    def test_current_cffdump_diff_marks_vfd_contract_resolved(self) -> None:
        current = diff.current_h3_registers()

        self.assertEqual(current["VFD_CNTL_0"], 0x303)
        self.assertEqual(current["VFD_CNTL_1"], 0xFCFCFC09)
        self.assertEqual(current["VFD_VERTEX_BUFFER[0].STRIDE"], 36)
        self.assertEqual(current["VFD_FETCH_INSTR[0].INSTR"], 0xC8200000)
        self.assertEqual(current["VFD_FETCH_INSTR[1].INSTR"], 0xC8200200)
        self.assertEqual(current["VFD_FETCH_INSTR[2].INSTR"], 0x44C00400)
        self.assertEqual(current["VFD_DEST_CNTL[0].INSTR"], 0xF)
        self.assertEqual(current["VFD_DEST_CNTL[1].INSTR"], 0x4F)
        self.assertEqual(current["VFD_DEST_CNTL[2].INSTR"], 0x81)

    def test_builder_manifest_records_bounded_delta(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3284-v3285-a640-magic-live-no-pixel-plus-v3286-cffdump-current-h3-diff"',
            source,
        )
        self.assertIn('"vfd_vs_source": VFD_VS_SOURCE', source)
        self.assertIn('"shader_payload": SHADER_PAYLOAD', source)
        self.assertIn('"vertex_stride_expected": VERTEX_STRIDE_EXPECTED', source)
        self.assertIn('"vfd_cntl0_expected": "0x00000303"', source)
        self.assertIn('"vfd_reg_writes_expected": VFD_REG_WRITES_EXPECTED', source)
        self.assertIn('"pm4_dwords_expected": PM4_DWORDS_EXPECTED', source)
        self.assertIn("PM4_DWORDS_EXPECTED = 335", source)
        self.assertIn("VFD_REG_WRITES_EXPECTED = 20", source)
        self.assertIn("gpu-h3-vfd-vs-contract-probe-candidate", source)


if __name__ == "__main__":
    unittest.main()
