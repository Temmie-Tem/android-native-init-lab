import hashlib
import importlib.util
import io
import struct
import sys
import tarfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_boot_verify.py"
P3 = ROOT / "workspace/public/src/scripts/revalidation/build_s22plus_direct_p3_boot.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def newc(entries):
    output = bytearray()
    for index, (name, mode, data) in enumerate(entries + [("TRAILER!!!", 0, b"")], 1):
        encoded = name.encode() + b"\0"
        fields = (index, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(encoded), 0)
        output += b"070701" + b"".join(f"{value:08x}".encode() for value in fields)
        output += encoded
        output += bytes((-len(output)) % 4)
        output += data
        output += bytes((-len(output)) % 4)
    return bytes(output)


def boot_v4(kernel=b"K" * 128, ramdisk=b"R" * 64):
    data = bytearray(12288)
    data[:8] = b"ANDROID!"
    struct.pack_into("<4I", data, 8, len(kernel), len(ramdisk), 0, 1584)
    struct.pack_into("<I", data, 40, 4)
    struct.pack_into("<I", data, 1580, 0)
    data[4096 : 4096 + len(kernel)] = kernel
    ramdisk_start = 8192 if len(kernel) > 4096 else 4096 + 4096
    if ramdisk_start + len(ramdisk) > len(data):
        data.extend(bytes(ramdisk_start + len(ramdisk) - len(data)))
    data[ramdisk_start : ramdisk_start + len(ramdisk)] = ramdisk
    return bytes(data)


def vendor_boot_v4(fragment=b"fragment", bootconfig=b"androidboot.test=1\n"):
    page = 4096
    ramdisk_start = page
    dtb_start = ramdisk_start + page
    table_start = dtb_start
    bootconfig_start = table_start + page
    total = bootconfig_start + len(bootconfig)
    data = bytearray(total)
    data[:8] = b"VNDRBOOT"
    struct.pack_into("<5I", data, 8, 4, page, 0x8000, 0x02000000, len(fragment))
    data[28 : 28 + len(b"console=null")] = b"console=null"
    struct.pack_into("<I", data, 2076, 0)
    data[2080 : 2080 + 4] = b"g0q\0"
    struct.pack_into("<2I", data, 2096, 2128, 0)
    struct.pack_into("<Q", data, 2104, 0)
    struct.pack_into("<4I", data, 2112, 108, 1, 108, len(bootconfig))
    data[ramdisk_start : ramdisk_start + len(fragment)] = fragment
    entry = bytearray(108)
    struct.pack_into("<3I", entry, 0, len(fragment), 0, 1)
    entry[12:20] = b"platform"
    data[table_start : table_start + 108] = entry
    data[bootconfig_start : bootconfig_start + len(bootconfig)] = bootconfig
    return bytes(data)


def static_aarch64_elf():
    entry_offset = 120
    entry_address = 0x400000 + entry_offset
    shoff = 128
    data = bytearray(shoff + 2 * 64)
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    struct.pack_into(
        "<16sHHIQQQIHHHHHH",
        data,
        0,
        ident,
        2,
        183,
        1,
        entry_address,
        64,
        shoff,
        0,
        64,
        56,
        1,
        64,
        2,
        0,
    )
    struct.pack_into("<IIQQQQQQ", data, 64, 1, 5, 0, 0x400000, 0, 128, 128, 0x1000)
    struct.pack_into("<2I", data, entry_offset, 0xD503205F, 0x17FFFFFF)
    struct.pack_into("<IIQQQQIIQQ", data, shoff + 64, 0, 1, 0x6, entry_address, entry_offset, 8, 0, 0, 4, 0)
    return bytes(data)


def ap_with_members(members):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, payload in members:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o644
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(payload))
    prefix = stream.getvalue()
    return prefix + f"{hashlib.md5(prefix).hexdigest()}  AP.tar\n".encode()


class S22PlusBootVerifyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load(SCRIPT, "s22plus_boot_verify_tested")
        cls.p3 = load(P3, "s22plus_p3_for_verify_test")

    def test_boot_v4_parser(self):
        parsed = self.module.parse_boot_v4(boot_v4())
        self.assertEqual(parsed.header["header_version"], 4)
        self.assertEqual(parsed.kernel, b"K" * 128)
        self.assertEqual(parsed.ramdisk, b"R" * 64)

    def test_vendor_boot_v4_table_parser(self):
        parsed = self.module.parse_vendor_boot_v4(vendor_boot_v4())
        self.assertEqual(parsed.header["table_entries"], 1)
        self.assertEqual(parsed.fragments[0].name, "platform")
        self.assertEqual(parsed.fragments[0].data, b"fragment")
        self.assertEqual(parsed.bootconfig, b"androidboot.test=1\n")

    def test_newc_normalization_and_duplicate_rejection(self):
        archive = newc([("init", 0o100750, b"elf"), ("etc", 0o040755, b"")])
        entries = self.module.parse_newc(archive)
        self.assertEqual(entries[0].name, "init")
        self.assertEqual(entries[0].file_type, "regular")
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_newc(newc([("init", 0o100750, b"a"), ("./init", 0o100750, b"b")]))
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_newc(newc([("../init", 0o100750, b"a")]))

    def test_aarch64_static_init_exact_entrypoint(self):
        result = self.module.inspect_aarch64_static_init(static_aarch64_elf())
        self.assertEqual(result["instructions"], ["wfe", "b <entrypoint>"])
        modified = bytearray(static_aarch64_elf())
        struct.pack_into("<I", modified, 120, 0xD4000001)
        with self.assertRaises(self.module.BootVerifyError):
            self.module.inspect_aarch64_static_init(bytes(modified))

    def test_ap_and_lz4_parsers(self):
        frame = self.p3.lz4_frame_store(b"raw-boot")
        ap = ap_with_members([("boot.img.lz4", frame)])
        structure, extracted = self.module.parse_ap_tar_md5(ap)
        self.assertEqual(structure["member"]["name"], "boot.img.lz4")
        self.assertEqual(extracted, frame)
        lz4 = self.module.parse_lz4_frame(frame)
        self.assertEqual(lz4["content_size"], len(b"raw-boot"))
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_lz4_frame(frame + b"trailing")

    def test_ap_rejects_extra_unsafe_and_bad_md5(self):
        frame = self.p3.lz4_frame_store(b"raw")
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_ap_tar_md5(
                ap_with_members([("boot.img.lz4", frame), ("extra", b"x")])
            )
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_ap_tar_md5(ap_with_members([("../bad", frame)]))
        valid = bytearray(ap_with_members([("boot.img.lz4", frame)]))
        valid[-41] = ord("0") if valid[-41] != ord("0") else ord("1")
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_ap_tar_md5(bytes(valid))

    def test_newc_rejects_nonzero_padding(self):
        archive = bytearray(newc([("aa", 0o100644, b"x")]))
        name_end = 110 + 3
        self.assertGreater((-name_end) % 4, 0)
        archive[name_end] = 1
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_newc(bytes(archive))

    def test_boot_and_vendor_header_mutations_fail_closed(self):
        bad_boot = bytearray(boot_v4())
        struct.pack_into("<I", bad_boot, 40, 3)
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_boot_v4(bytes(bad_boot))
        bad_vendor = bytearray(vendor_boot_v4())
        struct.pack_into("<I", bad_vendor, 2120, 2)
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_vendor_boot_v4(bytes(bad_vendor))

    def test_checker_module_is_evidence_isolated(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("s22plus_boot_slice", source)
        self.assertNotIn("build_s22plus", source)
        self.assertNotIn("subprocess.run([\"adb\"", source)
        self.assertNotIn("fastboot", source.lower())


if __name__ == "__main__":
    unittest.main()
