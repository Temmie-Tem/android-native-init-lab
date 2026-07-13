import hashlib
import importlib.util
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_lp_extract.py"


def load():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_lp_extract_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def checked_geometry(module, metadata_max_size=4096, slots=1, block_size=4096):
    block = bytearray(module.LP_METADATA_GEOMETRY_SIZE)
    struct.pack_into(
        "<II32sIII",
        block,
        0,
        module.LP_METADATA_GEOMETRY_MAGIC,
        module.GEOMETRY_STRUCT_SIZE,
        b"\0" * 32,
        metadata_max_size,
        slots,
        block_size,
    )
    block[8:40] = hashlib.sha256(block[:module.GEOMETRY_STRUCT_SIZE]).digest()
    return bytes(block)


def checked_metadata(module, image_size=65536, payload_sector=64):
    partition = struct.pack("<36sIIII", b"vendor", 1, 0, 1, 0)
    extent = struct.pack("<QIQI", 8, module.LP_TARGET_TYPE_LINEAR, payload_sector, 0)
    group = struct.pack("<36sIQ", b"default", 0, image_size)
    block = struct.pack("<QIIQ36sI", 40, 4096, 0, image_size, b"super", 0)
    tables = partition + extent + group + block
    header = bytearray(module.HEADER_V1_0_SIZE)
    struct.pack_into(
        "<IHHI32sI32s",
        header,
        0,
        module.LP_METADATA_HEADER_MAGIC,
        10,
        0,
        module.HEADER_V1_0_SIZE,
        b"\0" * 32,
        len(tables),
        hashlib.sha256(tables).digest(),
    )
    struct.pack_into("<III", header, 80, 0, 1, len(partition))
    struct.pack_into("<III", header, 92, len(partition), 1, len(extent))
    struct.pack_into("<III", header, 104, len(partition) + len(extent), 1, len(group))
    struct.pack_into(
        "<III", header, 116, len(partition) + len(extent) + len(group), 1, len(block)
    )
    checked = bytearray(header)
    checked[12:44] = b"\0" * 32
    header[12:44] = hashlib.sha256(checked).digest()
    slot = bytes(header) + tables
    return slot + b"\0" * (4096 - len(slot))


def synthetic_super(module, path, payload=b"P" * 4096):
    image = bytearray(65536)
    geometry = checked_geometry(module)
    image[4096:8192] = geometry
    image[8192:12288] = geometry
    metadata = checked_metadata(module)
    image[12288:16384] = metadata
    image[16384:20480] = metadata
    image[32768:32768 + len(payload)] = payload
    path.write_bytes(image)
    return payload


class S22PlusFyg8LpExtractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lp = load()

    def test_validates_and_extracts_selected_partition(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "super.img"
            payload = synthetic_super(self.lp, source)
            resolved, geometry, metadata, report = self.lp.inspect(source)
            self.assertEqual(resolved, source.resolve())
            self.assertEqual(geometry.metadata_max_size, 4096)
            self.assertEqual([item.name for item in metadata.partitions], ["vendor"])
            self.assertEqual(report["verdict"], "PASS_FYG8_LP_METADATA_VALIDATED_HOST_ONLY")
            result = self.lp.extract_partition(
                resolved, geometry, metadata, metadata.partitions[0], root / "out"
            )
            self.assertEqual((root / "out/vendor.img").read_bytes(), payload)
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())

    def test_rejects_geometry_checksum_corruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "super.img"
            synthetic_super(self.lp, source)
            with source.open("r+b") as stream:
                stream.seek(4096 + 12)
                byte = stream.read(1)
                stream.seek(4096 + 12)
                stream.write(bytes([byte[0] ^ 1]))
            with self.assertRaisesRegex(self.lp.LpError, "geometry blocks differ"):
                self.lp.inspect(source)

    def test_rejects_backup_metadata_difference(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "super.img"
            synthetic_super(self.lp, source)
            with source.open("r+b") as stream:
                stream.seek(16384 + 300)
                stream.write(b"X")
            with self.assertRaisesRegex(self.lp.LpError, "slot-0 metadata differ"):
                self.lp.inspect(source)

    def test_refuses_symlink_input_and_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "super.img"
            synthetic_super(self.lp, source)
            link = root / "link.img"
            os.symlink(source, link)
            with self.assertRaisesRegex(self.lp.LpError, "symlink input refused"):
                self.lp.inspect(link)
            resolved, geometry, metadata, _ = self.lp.inspect(source)
            output = root / "out"
            output.mkdir()
            (output / "vendor.img").write_bytes(b"existing")
            with self.assertRaisesRegex(self.lp.LpError, "output already exists"):
                self.lp.extract_partition(resolved, geometry, metadata, metadata.partitions[0], output)

    def test_main_refuses_symlink_output_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "super.img"
            synthetic_super(self.lp, source)
            real_output = root / "real-output"
            real_output.mkdir()
            linked_output = root / "linked-output"
            os.symlink(real_output, linked_output)
            self.assertEqual(
                self.lp.main(
                    [
                        str(source),
                        "--partition",
                        "vendor",
                        "--output-dir",
                        str(linked_output),
                    ]
                ),
                1,
            )
            self.assertFalse((real_output / "vendor.img").exists())

    def test_source_has_no_device_or_live_path(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn('"adb"', source.lower())
        self.assertNotIn('"odin"', source.lower())
        self.assertIn('"block_device_access": False', source)
        self.assertIn('"live_authorized": False', source)


if __name__ == "__main__":
    unittest.main()
