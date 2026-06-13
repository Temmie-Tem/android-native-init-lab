"""Regression tests for legacy root stage3 cleanup planning."""

from __future__ import annotations

import contextlib
import io
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation


cleanup = load_revalidation("cleanup_stage3_artifacts.py")


def args(**overrides):
    values = {
        "keep": list(cleanup.DEFAULT_KEEP),
        "execute": False,
        "include_boot_init": False,
    }
    values.update(overrides)
    return types.SimpleNamespace(**values)


def write_file(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class CleanupStage3ArtifactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.stage3 = self.root / "stage3"
        self.linux_init = self.stage3 / "linux_init"
        self.helpers = self.linux_init / "helpers"
        self.old_values = {
            "ROOT": cleanup.ROOT,
            "LEGACY_ROOT_STAGE3": cleanup.LEGACY_ROOT_STAGE3,
            "LINUX_INIT": cleanup.LINUX_INIT,
            "HELPERS": cleanup.HELPERS,
        }
        self.addCleanup(self.restore_constants)
        cleanup.ROOT = self.root
        cleanup.LEGACY_ROOT_STAGE3 = self.stage3
        cleanup.LINUX_INIT = self.linux_init
        cleanup.HELPERS = self.helpers

    def restore_constants(self) -> None:
        for name, value in self.old_values.items():
            setattr(cleanup, name, value)

    def test_build_tag_from_name_extracts_legacy_v_tags_only(self) -> None:
        self.assertEqual(cleanup.build_tag_from_name(Path("boot_linux_v724.img")), "v724")
        self.assertEqual(cleanup.build_tag_from_name(Path("init_v2189a")), "v2189a")
        self.assertEqual(cleanup.build_tag_from_name(Path("ramdisk_v725.cpio")), "v725")
        self.assertIsNone(cleanup.build_tag_from_name(Path("boot_linux_init.img")))
        self.assertIsNone(cleanup.build_tag_from_name(Path("helper-no-version")))

    def test_candidate_paths_finds_stage3_images_inits_helpers_and_optional_boot_init(self) -> None:
        keep_img = write_file(self.stage3 / "boot_linux_v724.img")
        stale_img = write_file(self.stage3 / "boot_linux_v999.img")
        stale_cpio = write_file(self.stage3 / "ramdisk_v999.cpio")
        stale_dir = self.stage3 / "ramdisk_v998"
        stale_dir.mkdir(parents=True)
        boot_init = write_file(self.stage3 / "boot_linux_init.img")
        init_bin = write_file(self.linux_init / "init_v999")
        helper_bin = write_file(self.helpers / "probe_v999")
        write_file(self.helpers / "probe_v999.txt")

        without_boot_init = set(cleanup.candidate_paths(include_boot_init=False))
        with_boot_init = set(cleanup.candidate_paths(include_boot_init=True))

        self.assertIn(keep_img, without_boot_init)
        self.assertIn(stale_img, without_boot_init)
        self.assertIn(stale_cpio, without_boot_init)
        self.assertIn(stale_dir, without_boot_init)
        self.assertIn(init_bin, without_boot_init)
        self.assertIn(helper_bin, without_boot_init)
        self.assertNotIn(boot_init, without_boot_init)
        self.assertIn(boot_init, with_boot_init)
        self.assertNotIn(self.helpers / "probe_v999.txt", with_boot_init)

    def test_main_dry_run_reports_kept_and_removable_without_deleting(self) -> None:
        kept = write_file(self.stage3 / "boot_linux_v724.img")
        stale = write_file(self.stage3 / "boot_linux_v999.img")
        boot_init = write_file(self.stage3 / "boot_linux_init.img")

        with (
            mock.patch.object(cleanup, "parse_args", return_value=args(include_boot_init=True)),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            rc = cleanup.main()

        output = stdout.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("mode: DRY-RUN", output)
        self.assertIn("kept: 1", output)
        self.assertIn("remove: 2", output)
        self.assertIn("remove stage3/boot_linux_v999.img", output)
        self.assertIn("remove stage3/boot_linux_init.img", output)
        self.assertTrue(kept.exists())
        self.assertTrue(stale.exists())
        self.assertTrue(boot_init.exists())

    def test_main_execute_removes_only_non_kept_candidates(self) -> None:
        kept = write_file(self.stage3 / "boot_linux_v724.img")
        stale = write_file(self.stage3 / "boot_linux_v999.img")
        boot_init = write_file(self.stage3 / "boot_linux_init.img")
        stale_dir = self.stage3 / "ramdisk_v999"
        stale_dir.mkdir(parents=True)
        write_file(stale_dir / "file")

        with (
            mock.patch.object(
                cleanup,
                "parse_args",
                return_value=args(keep=["v724"], execute=True, include_boot_init=True),
            ),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            rc = cleanup.main()

        output = stdout.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("mode: EXECUTE", output)
        self.assertTrue(kept.exists())
        self.assertFalse(stale.exists())
        self.assertFalse(boot_init.exists())
        self.assertFalse(stale_dir.exists())


if __name__ == "__main__":
    unittest.main()
