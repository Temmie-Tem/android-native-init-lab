from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
KMS_C = ROOT / "workspace/public/src/native-init/a90_kms.c"
KMS_H = ROOT / "workspace/public/src/native-init/a90_kms.h"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3335_gpu_z3_primary_setcrtc.py"
)


class NativeGpuZ3PrimarySetcrtcSourceV3335Tests(unittest.TestCase):
    def test_v3335_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3335")
        self.assertEqual(runner.INIT_VERSION, "0.11.103")
        self.assertEqual(runner.INIT_BUILD, "v3335-gpu-z3-primary-setcrtc")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3335_gpu_z3_primary_setcrtc.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.103", required)
        self.assertIn(b"v3335-gpu-z3-primary-setcrtc", required)
        self.assertIn(b"z3-imported-scanout-primary-probe", required)
        self.assertIn(b"gpu.z3.scanout.scope=gpu-z3-imported-scanout-primary-setcrtc", required)
        self.assertIn(b"gpu.z3.scanout.present_mode=primary-setcrtc-fullscreen", required)
        self.assertIn(b"gpu.z3.scanout.primary_setcrtc_attempted=1", required)
        self.assertIn(b"gpu.z3.scanout.kms.base_fb_id=", required)
        self.assertIn(b"restore_rc=", required)
        self.assertIn(b"z3-imported-scanout-primary-setcrtc-pass", required)

    def test_kms_external_fb_setcrtc_helper_exists(self) -> None:
        kms_c = KMS_C.read_text(encoding="utf-8")
        kms_h = KMS_H.read_text(encoding="utf-8")

        self.assertIn("int a90_kms_present_external_fb", kms_h)
        self.assertIn("a90_kms_present_external_fb(uint32_t fb_id", kms_c)
        self.assertIn("setcrtc.fb_id = fb_id;", kms_c)
        self.assertIn("DRM_IOCTL_MODE_SETCRTC", kms_c)

    def test_primary_probe_uses_fullscreen_dumb_and_restore(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("gpu_z3_imported_scanout_primary_summary_passed", source)
        self.assertIn("gpu_z3_imported_scanout_primary_probe", source)
        self.assertIn("z3-imported-scanout-primary-probe", source)
        self.assertIn("primary-setcrtc-fullscreen", source)
        self.assertIn("panel-fullscreen-from-kms-mode", source)
        self.assertIn("summary.kms_primary_setcrtc_attempted", source)
        self.assertIn("summary.kms_base_fb_id = kms_info.fb_id;", source)
        self.assertIn("dumb.width = primary_setcrtc ? summary.kms_screen_width", source)
        self.assertIn("dumb.height = primary_setcrtc ? summary.kms_screen_height", source)
        self.assertIn("a90_kms_present_external_fb(fb_id", source)
        self.assertIn("a90_kms_present_external_fb(summary.kms_base_fb_id", source)
        self.assertIn("summary.kms_restore_rc", source)

    def test_stride_aware_sampling_and_override_target(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("target_width_override", source)
        self.assertIn("target_stride_override", source)
        self.assertIn("GPU_Z3_PRIMARY_MAX_TARGET_BYTES", source)
        self.assertIn("row_words = session->target_stride / sizeof(uint32_t);", source)
        self.assertIn("words[((size_t)target_y * row_words) + target_x]", source)
        self.assertIn("src + ((uint64_t)y * session->target_stride)", source)

    def test_builder_manifest_records_primary_redirect(self) -> None:
        manifest = runner._minimal_gpu_z3_manifest()
        report = runner.render_report(
            {
                "decision": runner.DECISION,
                "boot_image": str(runner.BOOT_IMAGE),
                "boot_sha256": "0" * 64,
                "init_version": runner.INIT_VERSION,
                "init_build": runner.INIT_BUILD,
            },
            (),
            (),
        )

        self.assertEqual(
            manifest["primary_setcrtc_fix"],
            "render-directly-into-fullscreen-kms-dumb-fb-and-setcrtc",
        )
        self.assertIn("primary-setcrtc-present-rc-0", manifest["pass_requirements"])
        self.assertIn("base-fb-restore-rc-0", manifest["pass_requirements"])
        self.assertIn("SETCRTC", report)
        self.assertIn("stride-aware", report)


if __name__ == "__main__":
    unittest.main()
