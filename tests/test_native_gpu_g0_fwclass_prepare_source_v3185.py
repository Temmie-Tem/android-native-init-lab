from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3185_gpu_g0_fwclass_prepare.py"
)


class NativeGpuG0FwclassPrepareSourceV3185Tests(unittest.TestCase):
    def test_v3185_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3185")
        self.assertEqual(runner.INIT_VERSION, "0.11.21")
        self.assertEqual(runner.INIT_BUILD, "v3185-gpu-g0-fwclass-prepare")

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.21", required)
        self.assertIn(b"v3185-gpu-g0-fwclass-prepare", required)
        self.assertIn(b"gpu [g0-status|g0-fwclass-prepare|g0-open-probe", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.version=1", required)
        self.assertIn(b"/cache/a90-runtime/pkg/gpu-g0-fw", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.requires_private_sqe_gmu_staged=1", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.no_private_payload_in_ramdisk=1", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.no_power_writes=1", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.fwpath.write_rc=%d", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.result=ok", required)
        self.assertIn(b"a630_sqe.fw", required)
        self.assertIn(b"a640_gmu.bin", required)
        self.assertIn(b"a640_zap.b02", required)
        self.assertNotIn(b"gpu [g0-status|g0-open-probe", required)

    def test_dispatch_exposes_fwclass_prepare_fail_closed(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('strcmp(subcommand, "g0-fwclass-prepare")', source)
        self.assertIn('strcmp(subcommand, "fwclass-prepare")', source)
        self.assertIn("static int gpu_g0_fwclass_prepare(void)", source)
        self.assertIn('GPU_G0_RUNTIME_FW_DIR "/cache/a90-runtime/pkg/gpu-g0-fw"', source)
        self.assertIn("gpu_g0_verify_regular_file(\"verify_a630_sqe\"", source)
        self.assertIn("gpu_g0_verify_regular_file(\"verify_a640_gmu\"", source)
        self.assertIn("GPU_G0_FW_A630_SQE_SIZE 32304", source)
        self.assertIn("GPU_G0_FW_A640_GMU_SIZE 37680", source)
        self.assertIn("gpu_g0_copy_regular_file(zap_files[index].key", source)
        self.assertIn("gpu_g0_write_fwclass_path(GPU_G0_RUNTIME_FW_DIR)", source)
        self.assertIn("O_NOFOLLOW", source)
        self.assertIn('"gpu.g0.fwclass_prepare.no_private_payload_in_ramdisk=1', source)
        self.assertIn('"gpu.g0.fwclass_prepare.no_power_writes=1', source)

    def test_status_and_help_include_cache_firmware_paths(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")

        self.assertIn("fw_cache_a630_sqe", source)
        self.assertIn("fw_cache_a640_gmu", source)
        self.assertIn("fw_cache_a640_zap_mdt", source)
        self.assertIn("gpu [g0-status|g0-fwclass-prepare|g0-open-probe", source)
        self.assertIn("gpu [g0-status|g0-fwclass-prepare|g0-open-probe", basic)

    def test_builder_manifest_records_private_payload_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"gpu g0-fwclass-prepare"', source)
        self.assertIn('"ramdisk_private_firmware_payloads": 0', source)
        self.assertIn('"staged_private_inputs_required"', source)
        self.assertIn('"fresh-boot-dmesg-modem-ssr-correlation-check"', source)
        self.assertIn("NATIVE_INIT_V3184_GPU_G0_FWCLASS_LIVE_OPEN_SUCCESS_2026-06-25.md", source)
        self.assertIn('"GDSC-write"', source)
        self.assertIn('"freedreno-submit"', source)


if __name__ == "__main__":
    unittest.main()
