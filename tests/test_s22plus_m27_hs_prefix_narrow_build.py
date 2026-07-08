import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/build_s22plus_m27_hs_prefix_narrow.py")
SOURCE = Path("workspace/public/src/native-init/s22plus_init_m27_hs_prefix_download.c")
OUTPUT_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m27_hs_prefix_narrow_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("build_s22plus_m27_hs_prefix_narrow", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_single_member_tar(path: Path, member_name: str, payload: bytes = b"x") -> None:
    with tarfile.open(path, "w") as tar:
        info = tarfile.TarInfo(member_name)
        info.size = len(payload)
        info.mode = 0o644
        info.mtime = 0
        tar.addfile(info, fileobj=io.BytesIO(payload))


class S22PlusM27HsPrefixNarrowBuildTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_variant_constants(self):
        self.assertEqual(self.module.MARKER, "S22_NATIVE_INIT_M27_HS_PREFIX_DOWNLOAD")
        self.assertEqual(self.module.M27_MODULES_RAMDISK, "s22plus_m27_hs_only_usb2.modules")
        self.assertEqual(self.module.EXPECTED_HS_ONLY_COUNT, 40)
        self.assertEqual(self.module.DEFAULT_PREFIXES, (8, 12, 16, 20, 22, 23, 24))
        self.assertEqual(self.module.prefix_label(8), "P08")
        self.assertEqual(self.module.prefix_label(24), "P24")

    def test_source_is_download_discriminator_not_acm_park(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("S22_NATIVE_INIT_M27_HS_PREFIX_DOWNLOAD", text)
        self.assertIn("reboot_request=download", text)
        self.assertIn("modules_hs_only_usb2=/s22plus_m27_hs_only_usb2.modules", text)
        self.assertIn("module_count=40", text)
        self.assertIn("maximum_speed_dtbo=high-speed qmp_excluded=1", text)
        self.assertIn("sys_reboot(", text)
        self.assertNotIn("/config", text)
        self.assertNotIn("ttyGS0", text)
        self.assertNotIn("ss_acm.0", text)

    def test_default_prefixes_narrow_m26_p00_hit_to_p24_nohit(self):
        modules = self.module.EXPECTED_M25_HS_ONLY_SUBSET
        expected_next = {
            8: "debug-regulator.ko",
            12: "iommu-logger.ko",
            16: "qcom_iommu_util.ko",
            20: "sec_class.ko",
            22: "smem.ko",
            23: "socinfo.ko",
            24: "arm_smmu.ko",
        }
        self.assertEqual(tuple(expected_next), self.module.DEFAULT_PREFIXES)
        for count, next_module in expected_next.items():
            self.assertEqual(modules[count], next_module)
        self.assertNotIn(0, self.module.DEFAULT_PREFIXES)
        self.assertTrue(all(0 < count <= 24 for count in self.module.DEFAULT_PREFIXES))

    def test_load_m25_context_validates_manifest_module_list_and_dtbo_tars(self):
        modules = self.module.EXPECTED_M25_HS_ONLY_SUBSET
        module_text = "".join(f"{item}\n" for item in modules)
        with tempfile.TemporaryDirectory() as tmp_name:
            root = Path(tmp_name)
            out = root / "m25"
            build = out / "build"
            dtbo_candidate = out / "dtbo_candidate_odin4" / "AP.tar.md5"
            dtbo_rollback = out / "dtbo_stock_rollback_odin4" / "AP.tar.md5"
            build.mkdir(parents=True)
            dtbo_candidate.parent.mkdir(parents=True)
            dtbo_rollback.parent.mkdir(parents=True)
            (build / self.module.M25_MODULES_RAMDISK).write_text(module_text, encoding="ascii")
            write_single_member_tar(dtbo_candidate, "dtbo.img.lz4", b"candidate")
            write_single_member_tar(dtbo_rollback, "dtbo.img.lz4", b"rollback")
            manifest = {
                "target": "SM-S906N/g0q/S906NKSS7FYG8",
                "safety": {
                    "host_only_build": True,
                    "live_flash_authorized": False,
                },
                "dts_hs_only": {
                    "dts_hs_only": {
                        "subset": modules,
                        "subset_count": len(modules),
                        "blocked_dependency_edges": ["abc.ko"],
                        "blocklist": ["phy-msm-ssusb-qmp.ko"],
                        "subset_recovery_positions": {"dwc3-msm.ko": 262},
                    }
                },
                "hashes": {
                    "m25_hs_only_usb2": sha256_bytes(module_text.encode("ascii")),
                },
                "dtbo": {
                    "hashes": {
                        "candidate_ap_tar_md5": self.module.sha256_file(dtbo_candidate),
                        "patched_dtbo_raw": "patched",
                        "rollback_ap_tar_md5": self.module.sha256_file(dtbo_rollback),
                        "stock_dtbo_raw": "stock",
                    },
                    "paths": {
                        "candidate_ap_tar_md5": "m25/dtbo_candidate_odin4/AP.tar.md5",
                        "rollback_ap_tar_md5": "m25/dtbo_stock_rollback_odin4/AP.tar.md5",
                    },
                },
            }
            manifest_path = out / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            context = self.module.load_m25_hs_context(root, manifest_path)

        self.assertEqual(context["module_count"], 40)
        self.assertEqual(context["modules"], modules)
        self.assertEqual(context["module_text"], module_text)
        self.assertEqual(context["dtbo"]["candidate_ap_tar_md5_sha256"], manifest["dtbo"]["hashes"]["candidate_ap_tar_md5"])
        self.assertEqual(context["dtbo"]["stock_dtbo_rollback_ap_tar_md5_sha256"], manifest["dtbo"]["hashes"]["rollback_ap_tar_md5"])

    @unittest.skipUnless(OUTPUT_MANIFEST.exists(), "private M27 manifest missing")
    def test_current_output_manifest_is_narrow_p00_to_p24_matrix(self):
        data = json.loads(OUTPUT_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["purpose"], "M27 HS-only prefix-narrow discriminator matrix between P00 hit and P24 no-hit")
        self.assertEqual(data["safety"]["host_only_build"], True)
        self.assertEqual(data["safety"]["live_flash_authorized"], False)
        self.assertEqual(data["safety"]["device_action"], False)
        self.assertEqual(data["hs_only_modules"]["module_sha256"], "00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496")
        expected = [
            ("P08", 8, "debug-regulator.ko", "60669383e0345dfc5b7f50393ad6aebd3c67307ba32bc107c69eb324d67f499a"),
            ("P12", 12, "iommu-logger.ko", "3e0d65386966fb351a108f0c1e03dfdf695d365717e42552e970cfdab16af7ab"),
            ("P16", 16, "qcom_iommu_util.ko", "32b132e30c8f009e161ae0c71a64ed90d4b1ac1560302a17ef1309b03100f61f"),
            ("P20", 20, "sec_class.ko", "d4669c932312d2f84ce5982bc2df81a4903c23e7f6fae19bff4129aaba56afba"),
            ("P22", 22, "smem.ko", "1d7137f60d5743e0cb2145219e8806c6bc1b051a7d8a68749afe5b260cdf3643"),
            ("P23", 23, "socinfo.ko", "5bc8d767af7794bf7ece761b1d61d080e94b345e99be173556aece49ed40f8fb"),
            ("P24", 24, "arm_smmu.ko", "fff7ecf3ff9233f76ac17f07ecf56a383696d6ecb06b67f84ef39d8f08876180"),
        ]
        seen = [
            (entry["label"], entry["count"], entry["module_after_prefix"], entry["ap_tar_md5_sha256"])
            for entry in data["prefixes"]
        ]
        self.assertEqual(seen, expected)
        for label, _count, _next_module, _ap_sha in expected:
            ap = OUTPUT_MANIFEST.parent / label / "odin4" / "AP.tar.md5"
            self.assertEqual(self.module.tar_members(ap), ["boot.img.lz4"])


if __name__ == "__main__":
    unittest.main()
