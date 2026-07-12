import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_r2_audit.py"
SCRIPT_DIR = str(SCRIPT.parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_kernel_r2_audit_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8KernelR2AuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_config_comparison_allows_only_path_and_diagnostic_lto(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            stock = temp_path / "stock.config"
            generated = temp_path / "generated.config"
            stock.write_text(
                'CONFIG_LTO_CLANG_FULL=y\n# CONFIG_LTO_CLANG_THIN is not set\n'
                'CONFIG_UNUSED_KSYMS_WHITELIST="/stock/abi"\nCONFIG_MODVERSIONS=y\n',
                encoding="ascii",
            )
            generated.write_text(
                '# CONFIG_LTO_CLANG_FULL is not set\nCONFIG_LTO_CLANG_THIN=y\n'
                'CONFIG_UNUSED_KSYMS_WHITELIST="/local/abi"\nCONFIG_MODVERSIONS=y\n',
                encoding="ascii",
            )
            diagnostic = self.module.compare_configs(stock, generated, mode="diagnostic")
            strict = self.module.compare_configs(stock, generated, mode="r2")
        self.assertTrue(diagnostic["compatible_for_mode"])
        self.assertFalse(strict["compatible_for_mode"])

    def test_symbol_crc_closure_detects_missing_and_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            requirements = temp_path / "requirements.tsv"
            symvers = temp_path / "Module.symvers"
            requirements.write_text(
                "module\tsymbol\trequired_crc\tprovider_status\n"
                "a.ko\tgood\t0x11111111\tkernel-or-unresolved\n"
                "a.ko\tbad\t0x22222222\tkernel-or-unresolved\n"
                "a.ko\tmissing\t0x33333333\tkernel-or-unresolved\n",
                encoding="ascii",
            )
            symvers.write_text(
                "0x11111111\tgood\tvmlinux\tEXPORT_SYMBOL\n"
                "0x99999999\tbad\tvmlinux\tEXPORT_SYMBOL\n",
                encoding="ascii",
            )
            result = self.module.compare_symbol_requirements([requirements], [symvers])
        self.assertFalse(result["provider_crc_closed"])
        self.assertEqual(result["missing_unique_symbols"], 1)
        self.assertEqual(result["mismatched_unique_symbols"], 1)

    def test_image_metadata_requires_exact_stock_banner(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "Image"
            image_data = bytearray(8192)
            struct.pack_into("<Q", image_data, 0x10, len(image_data))
            image_data[0x38:0x3C] = b"ARM\x64"
            stock_banner = (
                "Linux version 5.10.226-android12-9-30958166-abS906NKSS7FYG8 "
                "(build-user@build-host) (Android (7284624, based on r416183b) "
                "clang version 12.0.5) #1 SMP PREEMPT Fri Aug 1 05:55:56 UTC 2025"
            )
            other_banner = stock_banner.replace(
                "Fri Aug 1 05:55:56 UTC 2025",
                "Sun Jul 12 07:16:46 UTC 2026",
            )
            encoded = other_banner.encode("ascii") + b"\n\x00"
            image_data[512:512 + len(encoded)] = encoded
            image.write_bytes(image_data)
            result = self.module.image_metadata(image, expected_banner=stock_banner)
            self.assertTrue(result["release_match"])
            self.assertTrue(result["compiler_match"])
            self.assertTrue(result["preempt_marker_present"])
            self.assertNotIn("\n", result["banner"])
            self.assertFalse(result["exact_banner_match"])

    def test_image_metadata_accepts_exact_stock_banner_before_newline(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "Image"
            image_data = bytearray(8192)
            struct.pack_into("<Q", image_data, 0x10, len(image_data))
            image_data[0x38:0x3C] = b"ARM\x64"
            stock_banner = (
                "Linux version 5.10.226-android12-9-30958166-abS906NKSS7FYG8 "
                "(build-user@build-host) (Android (7284624, based on r416183b) "
                "clang version 12.0.5) #1 SMP PREEMPT Fri Aug 1 05:55:56 UTC 2025"
            )
            encoded = stock_banner.encode("ascii") + b"\n\x00"
            image_data[512:512 + len(encoded)] = encoded
            image.write_bytes(image_data)

            result = self.module.image_metadata(image, expected_banner=stock_banner)

            self.assertEqual(result["banner"], stock_banner)
            self.assertTrue(result["exact_banner_match"])

    def test_canonical_banner_stops_at_lf_or_nul_without_normalizing(self):
        banner = b"Linux version 5.10.226-test #1 SMP PREEMPT exact"
        self.assertEqual(
            self.module.extract_linux_banner(banner + b"\x00trailing"),
            banner.decode("ascii"),
        )
        self.assertEqual(
            self.module.extract_linux_banner(banner + b"\ngarbage\x00"),
            banner.decode("ascii"),
        )
        without_preempt = "Linux version 5.10.226-test exact"
        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "Image"
            image_data = bytearray(8192)
            struct.pack_into("<Q", image_data, 0x10, len(image_data))
            image_data[0x38:0x3C] = b"ARM\x64"
            encoded = without_preempt.encode("ascii") + b"\x00"
            image_data[512:512 + len(encoded)] = encoded
            image.write_bytes(image_data)
            result = self.module.image_metadata(image, expected_banner=without_preempt)
        self.assertFalse(result["preempt_marker_present"])
        self.assertFalse(result["exact_banner_match"])

    def test_r2_remains_blocked_without_r1_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            image = temp_path / "Image"
            image_data = bytearray(8192)
            struct.pack_into("<Q", image_data, 0x10, len(image_data))
            image_data[0x38:0x3C] = b"ARM\x64"
            stock_banner = (
                b"Linux version 5.10.226-android12-9-30958166-abS906NKSS7FYG8 "
                b"(build-user@build-host) (Android (7284624, based on r416183b) "
                b"clang version 12.0.5) #1 SMP PREEMPT Fri Aug 1 05:55:56 UTC 2025"
            )
            generated_banner = stock_banner.replace(
                b"Fri Aug 1 05:55:56 UTC 2025",
                b"Sun Jul 12 07:16:46 UTC 2026",
            )
            encoded = generated_banner + b"\n\x00"
            image_data[512:512 + len(encoded)] = encoded
            image.write_bytes(image_data)
            config = temp_path / "config"
            stock_config = temp_path / "stock-config"
            config_text = (
                "CONFIG_LTO_CLANG_FULL=y\n# CONFIG_LTO_CLANG_THIN is not set\n"
                'CONFIG_UNUSED_KSYMS_WHITELIST="/local/abi"\n'
            )
            stock_text = config_text.replace("/local/abi", "/stock/abi")
            config.write_text(config_text, encoding="ascii")
            stock_config.write_text(stock_text, encoding="ascii")
            requirements = temp_path / "requirements.tsv"
            requirements.write_text(
                "module\tsymbol\trequired_crc\tprovider_status\n"
                "a.ko\tgood\t0x11111111\tkernel-or-unresolved\n",
                encoding="ascii",
            )
            symvers = temp_path / "Module.symvers"
            symvers.write_text("0x11111111\tgood\tvmlinux\tEXPORT_SYMBOL\n", encoding="ascii")
            stock = temp_path / "stock.json"
            stock.write_text(json.dumps({
                "target": self.module.TARGET,
                "linux_banner": stock_banner.decode("ascii"),
                "inputs": {"boot_img": {"size": 100663296}},
                "boot_header": {"ramdisk_size": 1024, "signature_size": 4096},
            }), encoding="ascii")
            module_map = temp_path / "module-map.json"
            module_map.write_text(json.dumps({
                "target": self.module.TARGET,
                "inputs": {"module_count": 441},
            }), encoding="ascii")
            corpus_layout = temp_path / "layout.json"
            corpus_layout.write_text(json.dumps({
                "schema": "s22plus_fyg8_super_module_layout_v1",
                "target": self.module.TARGET,
                "complete_on_disk_module_corpus": True,
                "complete_module_count": 491,
            }), encoding="ascii")
            with mock.patch.object(
                self.module,
                "EXPECTED_CORPUS_LAYOUT_SHA256",
                self.module.sha256_file(corpus_layout),
            ):
                result = self.module.audit(
                    ROOT,
                    mode="r2",
                    image=image,
                    generated_config=config,
                    symvers_paths=[symvers],
                    stock_baseline_path=stock,
                    stock_config=stock_config,
                    requirements=[requirements],
                    module_map_path=module_map,
                    corpus_layout_path=corpus_layout,
                    r1_result_path=None,
                )
        self.assertFalse(result["r2_static_pass"])
        self.assertIn("Full-LTO R1 PASS", " ".join(result["blockers"]))
        self.assertIn("differs from the exact FYG8 baseline", " ".join(result["blockers"]))


if __name__ == "__main__":
    unittest.main()
