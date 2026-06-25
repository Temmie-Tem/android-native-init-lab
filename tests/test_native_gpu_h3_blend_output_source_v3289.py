from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3289_gpu_h3_blend_output_probe.py"
)
audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)
diff = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_cffdump_diff_v3286.py"
)


class NativeGpuH3BlendOutputSourceV3289Tests(unittest.TestCase):
    def test_v3289_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3289")
        self.assertEqual(runner.INIT_VERSION, "0.11.70")
        self.assertEqual(runner.INIT_BUILD, "v3289-gpu-h3-blend-output-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3289_gpu_h3_blend_output_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.70", required)
        self.assertIn(b"v3289-gpu-h3-blend-output-probe", required)
        self.assertIn(b"gpu.h3.draw.blend_output_state_source=mesa-freedreno-a640-cffdump-draw2-direct-sysmem-compatible-blend-output-group", required)
        self.assertIn(b"gpu.h3.draw.shader_payload=verified-ir3-vs-r1xyzw-to-r2-position-preserve-r0-varying-and-cffdump-bary-fs", required)
        self.assertIn(b"gpu.h3.draw.sp_blend_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_blend_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_mrt0_blend_control=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_vs_const_config_reference_deferred=0x101-requires-vs-constant-buffer", required)

    def test_dispatch_sets_cffdump_blend_output_group(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H3_SP_BLEND_CNTL 0x00000100U", source)
        self.assertIn("#define GPU_H3_RB_BLEND_CNTL 0xffff0100U", source)
        self.assertIn("#define GPU_H3_RB_MRT0_BLEND_CONTROL 0x08040804U", source)
        self.assertIn("GPU_H2_REG_RB_BLEND_CNTL,\n                              GPU_H3_RB_BLEND_CNTL", source)
        self.assertIn("rb_mrt_control, GPU_H3_RB_MRT0_BLEND_CONTROL", source)
        self.assertIn("GPU_H2_REG_SP_BLEND_CNTL,\n                              GPU_H3_SP_BLEND_CNTL", source)
        self.assertIn("gpu.h3.draw.blend_output_state_source=mesa-freedreno-a640-cffdump-draw2-direct-sysmem-compatible-blend-output-group", source)
        self.assertIn("gpu.h3.draw.sp_blend_cntl=0x%x", source)
        self.assertIn("gpu.h3.draw.rb_blend_cntl=0x%x", source)
        self.assertIn("gpu.h3.draw.rb_mrt0_blend_control=0x%x", source)

    def test_shader_audit_tracks_v3289_blend_output(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(result["passed"])
        self.assertEqual(result["cycle"], "V3289")
        self.assertEqual(result["scope"], "gpu-h3-blend-output-state-shader-byte-audit")
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
        self.assertEqual(checks["sp_blend_cntl"], 0x100)
        self.assertEqual(checks["rb_blend_cntl"], 0xFFFF0100)
        self.assertEqual(checks["rb_mrt0_blend_control"], 0x08040804)
        self.assertTrue(checks["blend_output_group_matches_a640_cffdump_draw2"])

    def test_current_cffdump_diff_marks_blend_output_resolved(self) -> None:
        current = diff.current_h3_registers()

        self.assertEqual(current["SP_BLEND_CNTL"], 0x100)
        self.assertEqual(current["RB_BLEND_CNTL"], 0xFFFF0100)
        self.assertEqual(current["RB_MRT[0].BLEND_CONTROL"], 0x08040804)

    def test_builder_manifest_records_bounded_delta(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3288-vfd-vs-contract-live-no-pixel-plus-v3286-cffdump-blend-output-delta"',
            source,
        )
        self.assertIn('"blend_output_source": BLEND_OUTPUT_SOURCE', source)
        self.assertIn('"shader_payload": SHADER_PAYLOAD', source)
        self.assertIn('"sp_blend_cntl_expected": "0x00000100"', source)
        self.assertIn('"rb_blend_cntl_expected": "0xffff0100"', source)
        self.assertIn('"rb_mrt0_blend_control_expected": "0x08040804"', source)
        self.assertIn('"vfd_reg_writes_expected": VFD_REG_WRITES_EXPECTED', source)
        self.assertIn('"pm4_dwords_expected": PM4_DWORDS_EXPECTED', source)
        self.assertIn("PM4_DWORDS_EXPECTED = 335", source)
        self.assertIn("VFD_REG_WRITES_EXPECTED = 20", source)
        self.assertIn("gpu-h3-blend-output-probe-candidate", source)


if __name__ == "__main__":
    unittest.main()
