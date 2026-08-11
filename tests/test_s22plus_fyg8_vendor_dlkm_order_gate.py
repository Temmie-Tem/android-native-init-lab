import hashlib
import importlib.util
import io
import struct
import sys
import tarfile
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_vendor_dlkm_order_gate.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_vendor_dlkm_order_gate_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def sparse_fixture(*, trailing=b"", truncate=0):
    block = 4
    chunks = []
    raw = b"ABCDEFGH" + b"12341234" + b"\0" * 4 + b"WXYZ"
    chunks.append(struct.pack("<HHII", 0xCAC1, 0, 2, 12 + 8) + b"ABCDEFGH")
    chunks.append(struct.pack("<HHII", 0xCAC2, 0, 2, 12 + 4) + b"1234")
    chunks.append(struct.pack("<HHII", 0xCAC3, 0, 1, 12))
    chunks.append(struct.pack("<HHII", 0xCAC1, 0, 1, 12 + 4) + b"WXYZ")
    crc = zlib.crc32(raw) & 0xFFFFFFFF
    chunks.append(struct.pack("<HHII", 0xCAC4, 0, 0, 12 + 4) + struct.pack("<I", crc))
    header = struct.pack("<IHHHHIIII", 0xED26FF3A, 1, 0, 28, 12, block, 6, len(chunks), crc)
    sparse = header + b"".join(chunks) + trailing
    if truncate:
        sparse = sparse[:-truncate]
    return sparse, raw


class S22PlusFyg8VendorDlkmOrderGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def extract(self, sparse, raw, *, sparse_hash=None, raw_hash=None, range_hash=None):
        m = self.module
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "range.img"
            expected_range = raw[4:20]
            result = m.extract_sparse_range(
                io.BytesIO(sparse),
                output,
                range_offset=4,
                range_size=16,
                expected_sparse_size=len(sparse),
                expected_sparse_sha256=sparse_hash or hashlib.sha256(sparse).hexdigest(),
                expected_raw_size=len(raw),
                expected_raw_sha256=raw_hash or hashlib.sha256(raw).hexdigest(),
                expected_range_sha256=range_hash or hashlib.sha256(expected_range).hexdigest(),
            )
            return result, output.read_bytes()

    def test_sparse_range_crosses_raw_fill_and_dont_care(self):
        sparse, raw = sparse_fixture()
        result, data = self.extract(sparse, raw)
        self.assertEqual(data, b"EFGH12341234" + b"\0" * 4)
        self.assertEqual(result.raw_size, 24)
        self.assertEqual(result.raw_chunks, 2)
        self.assertEqual(result.fill_chunks, 1)
        self.assertEqual(result.dont_care_chunks, 1)
        self.assertEqual(result.crc32_chunks, 1)

    def test_truncated_sparse_stream_fails_closed_and_removes_output(self):
        sparse, raw = sparse_fixture(truncate=1)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "range.img"
            with self.assertRaises(self.module.GateError):
                self.module.extract_sparse_range(
                    io.BytesIO(sparse), output,
                    range_offset=4, range_size=16,
                    expected_sparse_size=len(sparse),
                    expected_sparse_sha256=hashlib.sha256(sparse).hexdigest(),
                    expected_raw_size=len(raw),
                    expected_raw_sha256=hashlib.sha256(raw).hexdigest(),
                    expected_range_sha256=hashlib.sha256(raw[4:20]).hexdigest(),
                )
            self.assertFalse(output.exists())

    def test_trailing_sparse_bytes_fail_closed(self):
        sparse, raw = sparse_fixture(trailing=b"x")
        with self.assertRaises(self.module.GateError):
            self.extract(sparse, raw)

    def test_sparse_raw_and_range_hashes_are_independent_gates(self):
        sparse, raw = sparse_fixture()
        for keyword in ("sparse_hash", "raw_hash", "range_hash"):
            with self.subTest(keyword=keyword):
                with self.assertRaises(self.module.GateError):
                    self.extract(sparse, raw, **{keyword: "0" * 64})

    def test_modules_load_shape_rejects_path_and_duplicate(self):
        m = self.module
        original_size = m.EXPECTED_MODULES_LOAD_SIZE
        original_hash = m.EXPECTED_MODULES_LOAD_SHA256
        try:
            good = b"a.ko\nb.ko\n"
            m.EXPECTED_MODULES_LOAD_SIZE = len(good)
            m.EXPECTED_MODULES_LOAD_SHA256 = hashlib.sha256(good).hexdigest()
            self.assertEqual(m.validate_modules_load_data(good), ("a.ko", "b.ko"))
            for bad in (b"dir/a.ko\nb.ko\n", b"a.ko\na.ko\n", b"a.ko\r\n"):
                m.EXPECTED_MODULES_LOAD_SIZE = len(bad)
                m.EXPECTED_MODULES_LOAD_SHA256 = hashlib.sha256(bad).hexdigest()
                with self.subTest(bad=bad), self.assertRaises(m.GateError):
                    m.validate_modules_load_data(bad)
        finally:
            m.EXPECTED_MODULES_LOAD_SIZE = original_size
            m.EXPECTED_MODULES_LOAD_SHA256 = original_hash

    def test_zip_tar_producer_streams_one_exact_member(self):
        m = self.module

        class NonClosingBytesIO(io.BytesIO):
            def close(self):
                self.was_closed = True

        payload = b"fixed-super-member"
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "firmware.zip"
            ap = io.BytesIO()
            with tarfile.open(fileobj=ap, mode="w") as tar:
                info = tarfile.TarInfo(m.SUPER_MEMBER)
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(m.AP_MEMBER, ap.getvalue())
            original_size = m.EXPECTED_SUPER_LZ4_SIZE
            try:
                m.EXPECTED_SUPER_LZ4_SIZE = len(payload)
                state = m.ProducerState()
                destination = NonClosingBytesIO()
                m.feed_super_member(archive_path, state, destination)
                self.assertIsNone(state.error)
                self.assertEqual(destination.getvalue(), payload)
                self.assertEqual(state.member_size, len(payload))
                self.assertEqual(state.member_sha256, hashlib.sha256(payload).hexdigest())
            finally:
                m.EXPECTED_SUPER_LZ4_SIZE = original_size

    def test_zip_tar_process_sparse_parser_seam_end_to_end(self):
        m = self.module
        sparse, raw = sparse_fixture()
        expected_range = raw[4:20]
        names = (
            "EXPECTED_SUPER_LZ4_SIZE",
            "EXPECTED_SPARSE_SUPER_SIZE",
            "EXPECTED_SPARSE_SUPER_SHA256",
            "EXPECTED_RAW_SUPER_SIZE",
            "EXPECTED_RAW_SUPER_SHA256",
            "VENDOR_DLKM_OFFSET",
            "VENDOR_DLKM_SIZE",
            "EXPECTED_VENDOR_DLKM_SHA256",
        )
        originals = {name: getattr(m, name) for name in names}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "firmware.zip"
            ap = io.BytesIO()
            with tarfile.open(fileobj=ap, mode="w") as tar:
                info = tarfile.TarInfo(m.SUPER_MEMBER)
                info.size = len(sparse)
                tar.addfile(info, io.BytesIO(sparse))
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(m.AP_MEMBER, ap.getvalue())
            passthrough = root / "lz4-passthrough"
            passthrough.write_text(
                "#!/usr/bin/python3\n"
                "import shutil, sys\n"
                "shutil.copyfileobj(sys.stdin.buffer, sys.stdout.buffer)\n",
                encoding="ascii",
            )
            passthrough.chmod(0o700)
            try:
                values = {
                    "EXPECTED_SUPER_LZ4_SIZE": len(sparse),
                    "EXPECTED_SPARSE_SUPER_SIZE": len(sparse),
                    "EXPECTED_SPARSE_SUPER_SHA256": hashlib.sha256(sparse).hexdigest(),
                    "EXPECTED_RAW_SUPER_SIZE": len(raw),
                    "EXPECTED_RAW_SUPER_SHA256": hashlib.sha256(raw).hexdigest(),
                    "VENDOR_DLKM_OFFSET": 4,
                    "VENDOR_DLKM_SIZE": 16,
                    "EXPECTED_VENDOR_DLKM_SHA256": hashlib.sha256(expected_range).hexdigest(),
                }
                for name, value in values.items():
                    setattr(m, name, value)
                output = root / "range.img"
                result, producer, returncode = m.stream_super_and_extract_range(
                    archive_path, passthrough, output, root / "stderr"
                )
                self.assertEqual(returncode, 0)
                self.assertEqual(producer.member_size, len(sparse))
                self.assertEqual(result.range_size, 16)
                self.assertEqual(output.read_bytes(), expected_range)
            finally:
                for name, value in originals.items():
                    setattr(m, name, value)

    def test_production_extent_and_space_arithmetic_are_pinned(self):
        m = self.module
        self.assertEqual(m.VENDOR_DLKM_OFFSET, 10_367_270_912)
        self.assertEqual(m.VENDOR_DLKM_SIZE, 57_610_240)
        self.assertEqual(m.VENDOR_DLKM_OFFSET + m.VENDOR_DLKM_SIZE, 10_424_881_152)
        self.assertEqual(m.VENDOR_DLKM_SIZE + m.MIN_FREE_MARGIN, 1_131_352_064)

    def test_dump_f2fs_multicall_name_is_not_symlink_resolved(self):
        m = self.module
        path = m.absolute_without_symlink_resolution(
            ROOT, Path("workspace/private/tools/f2fs-local/usr/sbin/dump.f2fs")
        )
        self.assertEqual(path.name, "dump.f2fs")


if __name__ == "__main__":
    unittest.main()
