from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3208_gpu_h1_shader_state_probe.py"
)


class NativeGpuH1ShaderStateProbeSourceV3208Tests(unittest.TestCase):
    def test_v3208_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3208")
        self.assertEqual(runner.INIT_VERSION, "0.11.31")
        self.assertEqual(runner.INIT_BUILD, "v3208-gpu-h1-shader-state-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3204_gpu_g5_kms_blit_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.31", required)
        self.assertIn(b"v3208-gpu-h1-shader-state-probe", required)
        self.assertIn(b"g5-kms-blit-probe", required)
        self.assertIn(b"gpu.g5.kms.version=1", required)
        self.assertIn(b"h1-shader-state-probe", required)
        self.assertIn(b"shader-state-probe", required)
        self.assertIn(b"gpu.h1.shader.version=1", required)
        self.assertIn(
            b"gpu.h1.shader.scope=first-triangle-h1-shader-upload-sp-state-no-draw",
            required,
        )
        self.assertIn(
            b"gpu.h1.shader.source=mesa-freedreno-a6xx-fd6-program-sp-state-plus-adreno-pm4-cp-load-state6",
            required,
        )
        self.assertIn(
            b"gpu.h1.shader.shader_source=hand-assembled-ir3-placeholder-no-full-compiler-no-execute",
            required,
        )
        self.assertIn(b"gpu.h1.shader.shader_execution_attempted=0", required)
        self.assertIn(b"gpu.h1.shader.draw_attempted=0", required)
        self.assertIn(b"gpu.h1.shader.kms_blit_attempted=0", required)
        self.assertIn(b"gpu.h1.shader.power_write_attempted=0", required)
        self.assertIn(b"gpu.h1.shader.proprietary_blob_attempted=0", required)
        self.assertIn(b"gpu.h1.shader.cmd_mmap_len=%llu", required)
        self.assertIn(b"gpu.h1.shader.vs_mmap_len=%llu", required)
        self.assertIn(b"gpu.h1.shader.fs_mmap_len=%llu", required)
        self.assertIn(b"gpu.h1.shader.cp_load_state6_geom=0x%x", required)
        self.assertIn(b"gpu.h1.shader.cp_load_state6_frag=0x%x", required)
        self.assertIn(b"shader-state-retired-no-draw", required)

    def test_dispatch_exposes_child_only_h1_shader_state_probe(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('strcmp(subcommand, "h1-shader-state-probe")', source)
        self.assertIn('strcmp(subcommand, "shader-state-probe")', source)
        self.assertIn("static int gpu_h1_shader_state_probe_child(int write_fd)", source)
        self.assertIn("static int gpu_h1_shader_state_probe(int timeout_ms", source)
        self.assertIn("struct gpu_h1_shader_state_probe_result", source)
        self.assertIn("GPU_H1_PM4_CP_LOAD_STATE6_GEOM 0x32U", source)
        self.assertIn("GPU_H1_PM4_CP_LOAD_STATE6_FRAG 0x34U", source)
        self.assertIn("GPU_H1_CP_LOAD_STATE6_SB_VS_SHADER (8U << 18)", source)
        self.assertIn("GPU_H1_CP_LOAD_STATE6_SB_FS_SHADER (12U << 18)", source)
        self.assertIn("GPU_H1_REG_SP_VS_CNTL_0 0xa800U", source)
        self.assertIn("GPU_H1_REG_SP_VS_PROGRAM_COUNTER_OFFSET 0xa81bU", source)
        self.assertIn("GPU_H1_REG_SP_VS_BASE 0xa81cU", source)
        self.assertIn("GPU_H1_REG_SP_VS_CONFIG 0xa823U", source)
        self.assertIn("GPU_H1_REG_SP_VS_INSTR_SIZE 0xa824U", source)
        self.assertIn("GPU_H1_REG_SP_PS_CNTL_0 0xa980U", source)
        self.assertIn("GPU_H1_REG_SP_PS_PROGRAM_COUNTER_OFFSET 0xa982U", source)
        self.assertIn("GPU_H1_REG_SP_PS_BASE 0xa983U", source)
        self.assertIn("GPU_H1_REG_SP_PS_CONFIG 0xab04U", source)
        self.assertIn("GPU_H1_REG_SP_PS_INSTR_SIZE 0xab05U", source)
        self.assertIn("gpu_h1_pm4_emit_load_state6_shader", source)
        self.assertIn("gpu_h1_build_shader_state_pm4", source)
        self.assertIn("GPU_IOCTL_KGSL_GPU_COMMAND", source)
        self.assertIn("GPU_IOCTL_KGSL_TIMESTAMP_EVENT", source)
        self.assertIn("GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID", source)
        self.assertIn("GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID", source)
        self.assertIn("GPU_IOCTL_KGSL_GPUOBJ_SYNC", source)
        self.assertIn("GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE", source)
        self.assertIn("result.cmd_mmap_len = cmd_alloc_arg.mmapsize", source)
        self.assertIn("result.vs_mmap_len = vs_alloc_arg.mmapsize", source)
        self.assertIn("result.fs_mmap_len = fs_alloc_arg.mmapsize", source)
        self.assertIn("munmap(cmd_map, (size_t)result.cmd_mmap_len)", source)
        self.assertIn("munmap(vs_map, (size_t)result.vs_mmap_len)", source)
        self.assertIn("munmap(fs_map, (size_t)result.fs_mmap_len)", source)
        self.assertIn('"gpu.h1.shader.parent_enters_open=0', source)
        self.assertIn('"gpu.h1.shader.parent_enters_ioctl=0', source)
        self.assertIn('"gpu.h1.shader.shader_execution_attempted=0', source)
        self.assertIn('"gpu.h1.shader.draw_attempted=0', source)
        self.assertIn('"gpu.h1.shader.kms_blit_attempted=0', source)
        self.assertIn('"gpu.h1.shader.power_write_attempted=0', source)
        self.assertIn('"gpu.h1.shader.proprietary_blob_attempted=0', source)
        self.assertIn("kill(pid, SIGKILL)", source)
        self.assertIn("waitpid(pid, &child_status, 0)", source)

        h1_start = source.index("static bool gpu_h1_build_shader_state_pm4")
        h1_end = source.index("static void gpu_g0_print_read_attr", h1_start)
        h1_stream = source[h1_start:h1_end]
        self.assertIn("GPU_G4_PM4_CP_WAIT_FOR_IDLE", h1_stream)
        self.assertIn("GPU_H1_PM4_CP_LOAD_STATE6_GEOM", h1_stream)
        self.assertIn("GPU_H1_PM4_CP_LOAD_STATE6_FRAG", h1_stream)
        self.assertNotIn("CP_DRAW_INDX_OFFSET", h1_stream)
        self.assertNotIn("a90_kms_present", h1_stream)

    def test_help_lists_h1_command(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")
        needle = "h1-shader-state-probe [--timeout-ms N] [--materialize-devnode]"
        self.assertIn(needle, source)
        self.assertIn(needle, basic)
        self.assertIn("g5-kms-blit-probe [--timeout-ms N] [--materialize-devnode]", source)
        self.assertIn("g5-kms-blit-probe [--timeout-ms N] [--materialize-devnode]", basic)

    def test_builder_manifest_records_h1_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"gpu h1-shader-state-probe --timeout-ms 5000 --materialize-devnode"', source)
        self.assertIn('"shader_execution_attempted": False', source)
        self.assertIn('"draw_attempted": False', source)
        self.assertIn('"kms_blit_attempted": False', source)
        self.assertIn('"full-ir3-compiler-port"', source)
        self.assertIn('"triangle-render"', source)
        self.assertIn('"shader-execution"', source)
        self.assertIn('"GDSC-write"', source)
        self.assertIn('"proprietary-adreno-blob"', source)
        self.assertIn("fd6_program.cc", source)
        self.assertIn("fd6_draw.cc", source)
        self.assertIn("a6xx.xml", source)
        self.assertIn("adreno_pm4.xml", source)
        self.assertIn("CP_LOAD_STATE6_GEOM", source)
        self.assertIn("CP_LOAD_STATE6_FRAG", source)
        self.assertIn("SP_VS_BASE", source)
        self.assertIn("SP_PS_BASE", source)
        self.assertIn("pending-gpu-h1-shader-state-live-validation", source)
        self.assertIn("preserve-v3204-ramdisk-overlay-v3208-init-helper-engine", source)
        self.assertIn("a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", source)
        self.assertIn("_patch_missing_audio_bundle_gate", source)
        self.assertIn("_overlay_preserved_v3204_ramdisk", source)
        self.assertIn("_finalize_manifest_after_overlay", source)


if __name__ == "__main__":
    unittest.main()
