from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3303_gpu_compute_c3_kms_probe.py"
)
c2_shader_bytes = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_compute_c2_pattern_shader_bytes_v3302.py"
)


class NativeGpuComputeC3KmsSourceV3303Tests(unittest.TestCase):
    def test_v3303_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3303")
        self.assertEqual(runner.INIT_VERSION, "0.11.77")
        self.assertEqual(runner.INIT_BUILD, "v3303-gpu-compute-c3-kms-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3303_gpu_compute_c3_kms_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.77", required)
        self.assertIn(b"v3303-gpu-compute-c3-kms-probe", required)
        self.assertIn(
            b"gpu.c3.kms.scope=visible-compute-c3-c2-uav-pattern-to-kms-held",
            required,
        )
        self.assertIn(b"gpu.c3.kms.result=compute-pattern-presented", required)
        self.assertIn(b"gpu.c3.vis.result=compute-pattern-presented-held", required)
        self.assertIn(b"gpu.c3.kms.snapshot_expected_match_count=%u", required)
        self.assertIn(b"GPU C3 COMPUTE VISUAL", required)

    def test_dispatch_contains_compute_pm4_contract(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_C1_PM4_CP_EXEC_CS 0x33U", source)
        self.assertIn("#define GPU_C1_CP_SET_MARKER_RM6_COMPUTE 8U", source)
        self.assertIn("#define GPU_C1_REG_SP_CS_CNTL_0 0xa9b0U", source)
        self.assertIn("#define GPU_C1_SP_CS_CNTL_0 0x80000080U", source)
        self.assertIn("#define GPU_C1_SP_CS_CONFIG 0x00400100U", source)
        self.assertIn("#define GPU_C1_SP_CS_CONST_CONFIG_0 0x00fcfcc0U", source)
        self.assertIn("#define GPU_C1_DESC0_R32_UINT_LINEAR 0x12c0a880U", source)
        self.assertIn("gpu_c2_build_compute_pm4", source)
        self.assertIn("GPU_C1_CP_LOAD_STATE6_STATE_TYPE_CONSTANTS", source)
        self.assertIn("GPU_C1_CP_LOAD_STATE6_STATE_TYPE_UAV", source)
        self.assertIn("GPU_C1_PM4_CP_EXEC_CS, 4", source)
        self.assertIn("GPU_G4_EVENT_CACHE_FLUSH_TS", source)

    def test_dispatch_embeds_c3_snapshot_and_kms_gate(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("0x200cc001U", source)
        self.assertIn("0xc0260000U", source)
        self.assertIn("0x03000000U", source)
        self.assertIn('GPU_C2_SNAPSHOT_PATH "/tmp/a90-gpu-c2-pattern-snapshot-v3302.u32"', source)
        self.assertIn("gpu.c2.compute.snapshot_write_rc=%d", source)
        self.assertIn("gpu.c3.kms.snapshot_expected_match_count=%u", source)
        self.assertIn("gpu.c3.kms.snapshot_mismatch_count=%u", source)
        self.assertIn('a90_kms_present("gpu-c3-compute-kms", true)', source)
        self.assertIn("compute-pattern-presented", source)
        self.assertIn("compute-pattern-presented-held", source)

    def test_builder_manifest_records_c3_live_validation(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn('"source_baseline": "v3302-compute-c2-pattern-live-readback-proof"', source)
        self.assertIn('"kms-present-compute-pattern-held"', source)
        self.assertIn("gpu-compute-c3-kms-probe-candidate", source)
        self.assertIn("gpu c3-compute-kms-probe --timeout-ms 5000 --hold-ms 30000 --materialize-devnode", source)

    def test_c2_shader_bytes_still_match_embedded_source(self) -> None:
        result = c2_shader_bytes.run_verification(require_disasm=False)

        self.assertTrue(result["passed"])
        self.assertEqual(result["shader"]["sizedwords"], 32)
        self.assertEqual(
            result["shader"]["binary_sha256"],
            "9259cd6e225aba4d1e86fb88527494404617b2aaf753c948379ade2edb18a6d1",
        )
        self.assertEqual(result["shader_contract"]["expected_readback_samples"]["16383"], 16383)


if __name__ == "__main__":
    unittest.main()
