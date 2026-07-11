import importlib.util
import gzip
import io
import stat
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_magisk_boot_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_magisk_boot_audit_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def align(value, boundary=4):
    return (value + boundary - 1) // boundary * boundary


def newc(entries):
    output = io.BytesIO()
    for index, (name, mode, data) in enumerate(entries + [("TRAILER!!!", 0, b"")], start=1):
        encoded_name = name.encode() + b"\0"
        fields = [index, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(encoded_name), 0]
        header = b"070701" + b"".join(f"{field:08x}".encode() for field in fields)
        output.write(header)
        output.write(encoded_name)
        output.write(b"\0" * (align(output.tell()) - output.tell()))
        output.write(data)
        output.write(b"\0" * (align(output.tell()) - output.tell()))
    return output.getvalue()


class S22PlusFyg8MagiskBootAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_parse_boot_v4_layout(self):
        header = bytearray(4096)
        header[:8] = b"ANDROID!"
        os_version = (12 << 25) | ((2025 - 2000) << 4) | 8
        struct.pack_into("<4I", header, 8, 3, 2, os_version, 1584)
        struct.pack_into("<I", header, 40, 4)
        struct.pack_into("<I", header, 1580, 4)
        image = bytes(header) + b"ker" + b"\0" * 4093 + b"rd" + b"\0" * 4094 + b"sig!"
        parsed = self.module.parse_boot_image(image)
        self.assertEqual(parsed["kernel"], b"ker")
        self.assertEqual(parsed["ramdisk"], b"rd")
        self.assertEqual(parsed["signature"], b"sig!")
        self.assertEqual(parsed["header"]["os_patch_level"], "2025-08")

    def test_parse_newc_preserves_mode_and_zero_mode_entry(self):
        archive = newc([
            ("init", stat.S_IFREG | 0o750, b"init-data"),
            (".backup/.magisk", stat.S_IFREG, b"SHA1=test\n"),
        ])
        parsed = self.module.parse_newc(archive)
        self.assertEqual(parsed["init"].data, b"init-data")
        self.assertEqual(stat.S_IMODE(parsed["init"].mode), 0o750)
        self.assertEqual(stat.S_IMODE(parsed[".backup/.magisk"].mode), 0)

    def test_parse_avb_footer(self):
        vbmeta = b"AVB0" + b"x" * 12
        body = b"image" + vbmeta
        footer = struct.pack("!4s2I3Q28s", b"AVBf", 1, 0, 5, 5, len(vbmeta), b"\0" * 28)
        parsed = self.module.parse_avb_footer(body + footer)
        self.assertEqual(parsed["version"], "1.0")
        self.assertEqual(parsed["original_image_size"], 5)
        self.assertEqual(parsed["vbmeta"], vbmeta)

    def test_diff_ranges(self):
        ranges = self.module.diff_ranges(b"abcdefghi", b"abXXefgYi")
        self.assertEqual([(item["start"], item["end_exclusive"]) for item in ranges], [(2, 4), (7, 8)])

    def test_extract_ikconfig_and_values(self):
        config = b"CONFIG_RKP=y\nCONFIG_PROCA=y\n"
        kernel = b"prefix" + self.module.IKCONFIG_START + gzip.compress(config) + self.module.IKCONFIG_END
        extracted = self.module.extract_ikconfig(kernel)
        self.assertEqual(extracted, config)
        self.assertEqual(
            self.module.config_values(extracted, ["CONFIG_RKP", "CONFIG_MISSING"]),
            {"CONFIG_RKP": "y", "CONFIG_MISSING": None},
        )

    def test_ramdisk_entry_audit_is_exhaustive(self):
        entry = self.module.CpioEntry
        regular = stat.S_IFREG | 0o644
        directory = stat.S_IFDIR | 0o755
        stock = {
            "init": entry("init", regular, 0, 0, 0, b"stock"),
            "dev": entry("dev", directory, 0, 0, 0, b""),
        }
        magisk = dict(stock)
        magisk["init"] = entry("init", regular, 0, 0, 0, b"magisk")
        for name in self.module.EXPECTED_MAGISK_ONLY_ENTRIES:
            magisk[name] = entry(name, regular, 0, 0, 0, b"")
        result = self.module.ramdisk_entry_audit(stock, magisk)
        self.assertTrue(result["complete_classification"])
        self.assertEqual(result["changed_entries"], ["init"])
        self.assertEqual(result["preserved_entries"], ["dev"])

    def test_kernel_patch_exactly_defex_and_proca(self):
        stock = b"prefix" + self.module.DEFEX_BEFORE + b"middle" + self.module.PROCA_BEFORE + b"suffix"
        magisk = stock.replace(self.module.DEFEX_BEFORE, self.module.DEFEX_AFTER).replace(
            self.module.PROCA_BEFORE, self.module.PROCA_AFTER
        )
        script = b" ".join([
            self.module.DEFEX_BEFORE.hex().upper().encode(),
            self.module.DEFEX_AFTER.hex().upper().encode(),
            self.module.PROCA_BEFORE.hex().upper().encode(),
            self.module.PROCA_AFTER.hex().upper().encode(),
            self.module.RKP_BEFORE.hex().upper().encode(),
            self.module.RKP_AFTER.hex().upper().encode(),
            self.module.LEGACY_SAR_BEFORE.hex().upper().encode(),
            self.module.LEGACY_SAR_AFTER.hex().upper().encode(),
        ])
        result = self.module.kernel_patch_audit(stock, magisk, script)
        self.assertTrue(result["exactly_defex_and_proca"])
        self.assertEqual(result["changed_bytes"], 9)
        self.assertEqual(len(result["diff_ranges"]), 2)


if __name__ == "__main__":
    unittest.main()
