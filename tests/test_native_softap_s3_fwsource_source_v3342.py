from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER_C = ROOT / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"


class NativeSoftapS3FwsourceSourceV3342Tests(unittest.TestCase):
    def test_qcacld_feeder_uses_mounted_vendor_source_first(self) -> None:
        source = HELPER_C.read_text(encoding="utf-8")

        self.assertIn("qcacld-fwsource-mounted-vendor-first", source)
        self.assertIn("const struct paths *paths", source)
        self.assertIn("paths->vendor_firmware", source)
        self.assertIn("paths->rfs_bridge_source_readonly_vendor_firmware", source)
        self.assertIn("paths->rfs_bridge_source_msm_mpss_readonly_vendor_firmware", source)

    def test_qcacld_source_reader_still_keeps_static_fallbacks(self) -> None:
        source = HELPER_C.read_text(encoding="utf-8")

        self.assertIn('"/mnt/vendor/firmware"', source)
        self.assertIn('"/proc/1/root/mnt/vendor/firmware"', source)
        self.assertIn('"/vendor/firmware"', source)
        self.assertIn('"/proc/1/root/vendor/firmware"', source)

    def test_feeder_calls_pass_paths_to_source_reader(self) -> None:
        source = HELPER_C.read_text(encoding="utf-8")

        self.assertIn("a90_qcacld_read_fw_source(paths,", source)
        self.assertIn("append_qcacld_firmware_class_fallback_feeder(stdout_buf,\n                                                                                 paths,", source)
        self.assertIn("a90_qcacld_feed_one_fw_fallback(stdout_buf,\n                                                phase,\n                                                (int)request_index,\n                                                paths,", source)


if __name__ == "__main__":
    unittest.main()
