import importlib.util
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_f2fs_module_corpus.py"


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_f2fs_module_corpus_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8F2FSModuleCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_parse_dentry_block_skips_continuation_slots(self):
        m = self.module
        data = bytearray(m.BLOCK_SIZE)

        def add(slot, inode, name, file_type):
            encoded = name.encode("utf-8")
            slots = (len(encoded) + 7) // 8
            for used in range(slot, slot + slots):
                data[used // 8] |= 1 << (used % 8)
            struct.pack_into(
                "<IIHB",
                data,
                m.DENTRY_BITMAP_BYTES + m.DENTRY_RESERVED_BYTES + slot * m.DENTRY_BYTES,
                0,
                inode,
                len(encoded),
                file_type,
            )
            start = m.FILENAME_OFFSET + slot * m.FILENAME_SLOT_BYTES
            data[start:start + len(encoded)] = encoded

        add(0, 3, ".", m.FILE_TYPE_DIRECTORY)
        add(1, 3, "..", m.FILE_TYPE_DIRECTORY)
        add(2, 11, "module-with-long-name.ko", m.FILE_TYPE_REGULAR)
        add(5, 12, "next.ko", m.FILE_TYPE_REGULAR)
        entries = m.parse_dentry_block(bytes(data))
        self.assertEqual([entry.name for entry in entries], [".", "..", "module-with-long-name.ko", "next.ko"])
        self.assertEqual(entries[2].inode, 11)

    def test_invalid_block_size_fails_closed(self):
        with self.assertRaises(self.module.CorpusError):
            self.module.parse_dentry_block(b"short")

    def test_expected_corpus_sizes_are_pinned(self):
        self.assertEqual(self.module.EXPECTED_VENDOR_DLKM_MODULES, 356)
        self.assertEqual(self.module.EXPECTED_REFERENCE_MODULES, 441)
        self.assertEqual(len(self.module.EXPECTED_VENDOR_DLKM_SHA256), 64)

    def test_multicall_dump_f2fs_path_is_not_symlink_resolved(self):
        path = self.module.absolute_without_symlink_resolution(
            ROOT, Path("workspace/private/tools/f2fs-local/usr/sbin/dump.f2fs")
        )
        self.assertEqual(path.name, "dump.f2fs")


if __name__ == "__main__":
    unittest.main()
