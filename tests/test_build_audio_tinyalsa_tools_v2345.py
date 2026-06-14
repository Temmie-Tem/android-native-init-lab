"""Host-only tests for the V2345 tinyalsa tool staging builder."""

from __future__ import annotations

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2345 = load_revalidation("build_audio_tinyalsa_tools_v2345")


class TinyalsaBuilderMetadata(unittest.TestCase):
    def test_pinned_source_and_tool_list_are_expected(self) -> None:
        self.assertEqual(v2345.RUN_ID, "V2345")
        self.assertEqual(v2345.BUILD_TAG, "v2345-audio-tinyalsa-tools")
        self.assertEqual(v2345.TINYALSA_COMMIT, "e14bf1479ebaaabf60bc4472ce8d304f72f03c32")
        self.assertEqual(v2345.TOOLS, ("tinymix", "tinypcminfo", "tinyplay"))
        self.assertIn(v2345.TINYALSA_COMMIT, v2345.TINYALSA_ARCHIVE_URL)
        self.assertIn("android.googlesource.com/platform/external/tinyalsa", v2345.TINYALSA_TREE_URL)
        self.assertIn("-static", v2345.CFLAGS)

    def test_safe_extract_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Path(tempdir) / "evil.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                payload = b"bad"
                info = tarfile.TarInfo("../evil.txt")
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))

            with self.assertRaises(RuntimeError):
                v2345.safe_extract_tar_gz(archive, Path(tempdir) / "out")

    def test_safe_extract_rejects_links(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Path(tempdir) / "link.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("src/link")
                info.type = tarfile.SYMTYPE
                info.linkname = "/etc/passwd"
                tar.addfile(info)

            with self.assertRaises(RuntimeError):
                v2345.safe_extract_tar_gz(archive, Path(tempdir) / "out")

    def test_safe_extract_accepts_normal_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            archive = Path(tempdir) / "ok.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                payload = b"ok"
                info = tarfile.TarInfo("src/file.txt")
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))

            out = Path(tempdir) / "out"
            v2345.safe_extract_tar_gz(archive, out)
            self.assertEqual((out / "src/file.txt").read_bytes(), b"ok")


if __name__ == "__main__":
    unittest.main()
