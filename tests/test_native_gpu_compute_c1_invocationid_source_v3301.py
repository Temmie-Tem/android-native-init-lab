from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3301_gpu_compute_c1_invocationid_probe.py"
)
shader_bytes = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_compute_c1_shader_bytes_v3300.py"
)


class NativeGpuComputeC1InvocationidSourceV3301Tests(unittest.TestCase):
    def test_v3301_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3301")
        self.assertEqual(runner.INIT_VERSION, "0.11.75")
        self.assertEqual(runner.INIT_BUILD, "v3301-gpu-compute-c1-invocationid-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3301_gpu_compute_c1_invocationid_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.75", required)
        self.assertIn(b"v3301-gpu-compute-c1-invocationid-probe", required)
        self.assertIn(
            b"gpu.c1.compute.scope=visible-compute-c1-invocationid-uav-readback",
            required,
        )
        self.assertIn(b"gpu.c1.compute.result=invocationid-uav-readback-pass", required)
        self.assertIn(b"gpu.c1.compute.expected_readback=0..31", required)
        self.assertIn(b"INVOCATIONID UAV READBACK", required)

    def test_dispatch_contains_compute_pm4_contract(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_C1_PM4_CP_EXEC_CS 0x33U", source)
        self.assertIn("#define GPU_C1_CP_SET_MARKER_RM6_COMPUTE 8U", source)
        self.assertIn("#define GPU_C1_REG_SP_CS_CNTL_0 0xa9b0U", source)
        self.assertIn("#define GPU_C1_SP_CS_CNTL_0 0x80000080U", source)
        self.assertIn("#define GPU_C1_SP_CS_CONFIG 0x00400100U", source)
        self.assertIn("#define GPU_C1_SP_CS_CONST_CONFIG_0 0x00fcfcc0U", source)
        self.assertIn("#define GPU_C1_DESC0_R32_UINT_LINEAR 0x12c0a880U", source)
        self.assertIn("gpu_c1_build_compute_pm4", source)
        self.assertIn("GPU_C1_CP_LOAD_STATE6_STATE_TYPE_CONSTANTS", source)
        self.assertIn("GPU_C1_CP_LOAD_STATE6_STATE_TYPE_UAV", source)
        self.assertIn("GPU_C1_PM4_CP_EXEC_CS, 4", source)
        self.assertIn("GPU_G4_EVENT_CACHE_FLUSH_TS", source)

    def test_dispatch_embeds_verified_shader_and_readback_gate(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("0x200cc001U", source)
        self.assertIn("0xc0260000U", source)
        self.assertIn("0x03000000U", source)
        self.assertIn("gpu.c1.compute.shader_sha256=7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a", source)
        self.assertIn("gpu.c1.compute.kernel_sha256=1e0187f2917ab504602a22f30f475716ea8ec7f7123481d371cc87b908c1a97a", source)
        self.assertIn("gpu.c1.compute.expected_readback=0..31", source)
        self.assertIn("result.expected_match_count == GPU_C1_UAV_WORDS", source)
        self.assertIn("result.mismatch_count == 0U", source)
        self.assertIn("invocationid-uav-readback-pass", source)

    def test_builder_manifest_records_c1_live_validation(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn('"source_baseline": "v3300-compute-c1-verified-shader-bytes"', source)
        self.assertIn('"uav-readback-buf-i-equals-i"', source)
        self.assertIn("gpu-compute-c1-invocationid-probe-candidate", source)
        self.assertIn("gpu c1-compute-invocationid-probe --timeout-ms 5000 --materialize-devnode", source)

    def test_v3300_shader_bytes_still_match_embedded_source(self) -> None:
        result = shader_bytes.run_verification(require_disasm=False)

        self.assertTrue(result["passed"])
        self.assertEqual(result["shader"]["sizedwords"], 32)
        self.assertEqual(
            result["shader"]["binary_sha256"],
            "7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a",
        )
        self.assertEqual(result["kernel_contract"]["expected_readback"], list(range(32)))


if __name__ == "__main__":
    unittest.main()
