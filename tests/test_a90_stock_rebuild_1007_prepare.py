"""Host-only tests for the A90 Snapdragon LLVM 10.0.7 source preparer."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / (
    "workspace/public/src/scripts/revalidation/a90_stock_rebuild_1007_prepare.py"
)
CRLF_PATHS = (
    "scripts/Makefile.lib",
    "drivers/input/wacom/Makefile",
    "drivers/gpu/drm/msm/samsung_lego/SELF_DISPLAY/Makefile",
)
AUDIO_SOC_FILES = (
    "core.h",
    "pinctrl-utils.h",
    "wcd-spi-ac.c",
    "wcd_spi_ctl_v01.c",
    "wcd_spi_ctl_v01.h",
)
AUDIO_INCLUDE_DIRS = ("soc", "dsp", "ipc", "uapi", "asoc")


def write(root: Path, relative: str, data: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def materialize_minimal_tree(root: Path) -> None:
    for relative in CRLF_PATHS:
        write(root, relative, b"first\r\nsecond\r\n")
    for name in ("ion.h", "msm_ion.h"):
        write(root, f"drivers/staging/android/uapi/{name}", name.encode())
    for name in AUDIO_SOC_FILES:
        write(root, f"techpack/audio/4.0/soc/{name}", name.encode())
    for subdir in AUDIO_INCLUDE_DIRS:
        write(
            root,
            f"techpack/audio/4.0/include/{subdir}/fixture.h",
            f"{subdir}-fixture".encode(),
        )


def run_prepare(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-root",
            str(root),
            "--receipt",
            str(root.parent / "receipt.json"),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class A90StockRebuild1007PrepareTests(unittest.TestCase):
    def test_exact_preparation_changes_no_semantic_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Kernel"
            materialize_minimal_tree(root)
            completed = run_prepare(root)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["schema"], "a90-stock-rebuild-1007-host-preparation-v1")
            self.assertEqual(receipt["semanticSourceChanges"], 0)
            self.assertEqual(len(receipt["normalizedLineEndings"]), 3)
            self.assertEqual(len(receipt["exactByteCopies"]), 12)
            self.assertEqual(receipt["existingIncludesPreserved"], [])
            self.assertEqual(len(receipt["workspaceSymlinks"]), 2)
            for relative in CRLF_PATHS:
                self.assertEqual((root / relative).read_bytes(), b"first\nsecond\n")
            self.assertEqual(
                (root / "include/uapi/linux/ion.h").read_bytes(), b"ion.h"
            )
            for version in ("msm-4.14", "msm-4.19"):
                link = root / "out/kernel" / version / "techpack/audio"
                self.assertTrue(link.is_symlink())
                self.assertEqual(link.resolve(), root / "techpack/audio")

    def test_existing_audio_include_is_preserved_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Kernel"
            materialize_minimal_tree(root)
            target = write(root, "techpack/audio/include/soc/fixture.h", b"vendor-existing")
            completed = run_prepare(root)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual(target.read_bytes(), b"vendor-existing")
            preserved = receipt["existingIncludesPreserved"]
            self.assertEqual(len(preserved), 1)
            self.assertEqual(preserved[0]["kind"], "regular")

    def test_existing_copy_target_with_different_bytes_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Kernel"
            materialize_minimal_tree(root)
            write(root, "include/uapi/linux/ion.h", b"wrong")
            completed = run_prepare(root)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("existing target differs", completed.stderr)

    def test_symlink_escape_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "Kernel"
            materialize_minimal_tree(root)
            outside = write(base, "outside-ion.h", b"ion.h")
            target = root / "include/uapi/linux/ion.h"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(outside)
            completed = run_prepare(root)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("existing symlink escapes source root", completed.stderr)

    def test_unexpected_line_ending_shape_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "Kernel"
            materialize_minimal_tree(root)
            (root / CRLF_PATHS[0]).write_bytes(b"already-lf\n")
            completed = run_prepare(root)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unexpected line-ending shape", completed.stderr)


if __name__ == "__main__":
    unittest.main()
