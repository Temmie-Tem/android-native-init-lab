from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
HELPER_C = ROOT / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3342_softap_s3_fwsource_iftype_probe.py"
)


class BuildNativeInitBootV3342SoftapS3FwsourceIftypeProbeTests(unittest.TestCase):
    def test_v3342_identity(self) -> None:
        self.assertEqual(runner.CYCLE, "V3342")
        self.assertEqual(runner.INIT_VERSION, "0.11.106")
        self.assertEqual(runner.INIT_BUILD, "v3342-softap-s3-fwsource-iftype-probe")
        self.assertEqual(
            runner.EXPECTED_HELPER_SHA256,
            "fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef",
        )
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3342_softap_s3_fwsource_iftype_probe.img",
        )
        self.assertEqual(runner.BASE_BOOT.name, "boot_linux_v3335_gpu_z3_primary_setcrtc.img")

    def test_required_strings_include_fwsource_policy(self) -> None:
        required = b"\n".join(runner.REQUIRED_STRINGS)

        self.assertIn(b"0.11.106", required)
        self.assertIn(b"v3342-softap-s3-fwsource-iftype-probe", required)
        self.assertIn(b"a90.doomgeneric.v3342.tick_telemetry=smooth-demo-paced-time-direct-blit", required)
        self.assertIn(b"a90.doomgeneric.v3342.audio=real-sfx-pcm-stream-softap-s3-fwsource-iftype-probe", required)
        self.assertIn(b"softap-iftype-probe-pass", required)
        self.assertIn(b"qcacld-fwsource-mounted-vendor-first", required)
        self.assertIn(b"source_policy=qcacld-fwsource-mounted-vendor-first", required)

    def test_softap_manifest_names_fwsource_gate(self) -> None:
        manifest = runner._softap_manifest()

        self.assertEqual(manifest["rung"], "S3-lower-gate")
        self.assertEqual(manifest["scope"], "softap-fwsource-mounted-vendor-iftype-probe-no-ap-start")
        self.assertIn("wifi softap iftype-probe", manifest["commands"])
        self.assertEqual(
            manifest["helper_route"]["source_policy"],
            "qcacld-fwsource-mounted-vendor-first",
        )
        self.assertIn("version-0.11.106", manifest["pass_requirements"])
        self.assertNotIn("version-0.11.105", manifest["pass_requirements"])
        self.assertIn("qcacld-fwclass-feed-source-rc-0", manifest["pass_requirements"])

    def test_softap_manifest_uses_original_v3341_manifest_after_patch(self) -> None:
        original = runner.previous._softap_manifest
        try:
            runner.previous._softap_manifest = runner._softap_manifest
            manifest = runner._softap_manifest()
        finally:
            runner.previous._softap_manifest = original

        self.assertEqual(manifest["rung"], "S3-lower-gate")
        self.assertEqual(
            manifest["helper_route"]["source_policy"],
            "qcacld-fwsource-mounted-vendor-first",
        )

    def test_report_describes_mounted_vendor_source_fix(self) -> None:
        report = runner.render_report(
            {
                "boot_image": str(runner.BOOT_IMAGE),
                "boot_sha256": "0" * 64,
                "helper_sha256": "1" * 64,
            },
            (runner.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG,),
            (),
        )

        self.assertIn("V3342", report)
        self.assertIn("0.11.106", report)
        self.assertIn("mounted read-only vendor firmware tree", report)
        self.assertIn("qcacld-fwsource-mounted-vendor-first", report)
        self.assertIn("no `wpa_supplicant mode=2`", report)

    def test_current_helper_source_contains_fwsource_fix(self) -> None:
        source = HELPER_C.read_text(encoding="utf-8")

        self.assertIn("qcacld-fwsource-mounted-vendor-first", source)
        self.assertIn("paths->vendor_firmware", source)
        self.assertIn("a90_qcacld_read_fw_source(paths,", source)


if __name__ == "__main__":
    unittest.main()
