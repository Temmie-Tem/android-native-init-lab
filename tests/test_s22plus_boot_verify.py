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
        self.assertEqual(
            self.module.decompress_lz4_frame_python(frame), b"raw-boot"
        )
        compressed_block = b"\x44abcd\x04\x00"
        descriptor = bytes((0x68, 0x70)) + (12).to_bytes(8, "little")
        compressed_frame = (
            b"\x04\x22\x4d\x18"
            + descriptor
            + bytes(((self.module.xxh32(descriptor) >> 8) & 0xFF,))
            + len(compressed_block).to_bytes(4, "little")
            + compressed_block
            + b"\x00\x00\x00\x00"
        )
        self.assertEqual(
            self.module.decompress_lz4_frame_python(compressed_frame),
            b"abcdabcdabcd",
        )
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_lz4_frame(frame + b"trailing")

    def test_lz4_rejects_header_block_and_content_checksum_corruption(self):
        payload = b"checksum-payload"
        flg = 0x7C
        descriptor = bytes((flg, 0x70)) + len(payload).to_bytes(8, "little")
        frame = (
            b"\x04\x22\x4d\x18"
            + descriptor
            + bytes(((self.module.xxh32(descriptor) >> 8) & 0xFF,))
            + (0x80000000 | len(payload)).to_bytes(4, "little")
            + payload
            + self.module.xxh32(payload).to_bytes(4, "little")
            + b"\x00\x00\x00\x00"
            + self.module.xxh32(payload).to_bytes(4, "little")
        )
        self.assertEqual(self.module.decompress_lz4_frame_python(frame), payload)
        corruptions = {
            "header": 14,
            "block": 19 + len(payload),
            "content": len(frame) - 1,
        }
        for name, offset in corruptions.items():
            with self.subTest(name=name):
                changed = bytearray(frame)
                changed[offset] ^= 1
                with self.assertRaises(self.module.BootVerifyError):
                    self.module.decompress_lz4_frame_python(bytes(changed))
                with self.assertRaises(self.module.BootVerifyError):
                    self.module.parse_lz4_frame(bytes(changed))

    def test_lz4_rejects_dictionary_and_dependent_block_frames(self):
        payload = b"x"
        dictionary_descriptor = (
            bytes((0x69, 0x70))
            + len(payload).to_bytes(8, "little")
            + (7).to_bytes(4, "little")
        )
        dictionary_frame = (
            b"\x04\x22\x4d\x18"
            + dictionary_descriptor
            + bytes(
                ((self.module.xxh32(dictionary_descriptor) >> 8) & 0xFF,)
            )
            + (0x80000001).to_bytes(4, "little")
            + payload
            + b"\x00\x00\x00\x00"
        )
        with self.assertRaisesRegex(self.module.BootVerifyError, "dictionary"):
            self.module.decompress_lz4_frame_python(dictionary_frame)

        dependent_descriptor = bytes((0x48, 0x70)) + len(payload).to_bytes(
            8, "little"
        )
        dependent_frame = (
            b"\x04\x22\x4d\x18"
            + dependent_descriptor
            + bytes(((self.module.xxh32(dependent_descriptor) >> 8) & 0xFF,))
            + (0x80000001).to_bytes(4, "little")
            + payload
            + b"\x00\x00\x00\x00"
        )
        with self.assertRaisesRegex(self.module.BootVerifyError, "dependent"):
            self.module.decompress_lz4_frame_python(dependent_frame)
        with self.assertRaisesRegex(self.module.BootVerifyError, "dependent"):
            self.module.parse_lz4_frame(dependent_frame)

    def test_ap_rejects_extra_unsafe_and_bad_md5(self):
        frame = self.p3.lz4_frame_store(b"raw")
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_ap_tar_md5(
                ap_with_members([("boot.img.lz4", frame), ("extra", b"x")])
            )
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_ap_tar_md5(ap_with_members([("../bad", frame)]))
        with self.assertRaisesRegex(self.module.BootVerifyError, "prefix"):
            self.module.parse_ap_tar_md5(
                ap_with_members([("a" * 101 + "/boot.img.lz4", frame)])
            )
        valid = bytearray(ap_with_members([("boot.img.lz4", frame)]))
        valid[-41] = ord("0") if valid[-41] != ord("0") else ord("1")
        with self.assertRaises(self.module.BootVerifyError):
            self.module.parse_ap_tar_md5(bytes(valid))

    def test_real_candidate_and_rollback_match_external_lz4_decoder(self):
        lz4 = ROOT / (
            "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/"
            "kernel_platform/prebuilts/kernel-build-tools/linux-x86/bin/lz4"
        )
        cases = (
            (
                ROOT
                / "workspace/private/outputs/s22plus_fyg8_p234/"
                "candidate-a/odin4/AP.tar.md5",
                True,
            ),
            (
                ROOT
                / "workspace/private/outputs/s22plus_magisk_root_boot_only/"
                "AP.tar.md5",
                False,
            ),
        )
        if not lz4.is_file() or not all(path.is_file() for path, _strict in cases):
            self.skipTest("exact private APs or pinned external LZ4 are unavailable")
        for path, strict in cases:
            with self.subTest(path=path.name, deterministic_metadata=strict):
                _structure, frame = self.module.parse_ap_tar_md5(
                    path.read_bytes(), require_deterministic_metadata=strict
                )
                self.assertEqual(
                    self.module.decompress_lz4_frame_python(frame),
                    self.module.decompress_lz4(lz4, frame),
                )

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
