"""Regression tests for build_native_init_boot_v724."""

from __future__ import annotations

import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v724")


class BuildNativeInitBootV724(unittest.TestCase):
    def test_pid1_sources_includes_default_and_skips_a90_main_programs(self) -> None:
        old_linux_init = builder.LINUX_INIT
        old_default_source = builder.DEFAULT_INIT_SOURCE
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                source_root = Path(temp_dir)
                default_source = source_root / "init_v724.c"
                default_source.write_text("void init_entry(void) {}\n", encoding="utf-8")
                library_source = source_root / "a90_qrtr.c"
                library_source.write_text("void helper(void) {}\n", encoding="utf-8")
                standalone_source = source_root / "a90_tool.c"
                standalone_source.write_text("int main(void) { return 0; }\n", encoding="utf-8")

                builder.LINUX_INIT = source_root
                builder.DEFAULT_INIT_SOURCE = default_source

                sources = builder.pid1_sources()
        finally:
            builder.LINUX_INIT = old_linux_init
            builder.DEFAULT_INIT_SOURCE = old_default_source

        self.assertEqual(sources[0], default_source)
        self.assertIn(library_source, sources)
        self.assertNotIn(standalone_source, sources)

    def test_build_init_uses_static_pid1_sources_strip_and_file_checks(self) -> None:
        old_pid1_sources = builder.pid1_sources
        old_run = builder.run
        commands: list[list[str | Path]] = []
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_binary = Path(temp_dir) / "build" / "init_v724"
                source_one = Path(temp_dir) / "init_v724.c"
                source_two = Path(temp_dir) / "a90_qrtr.c"
                builder.pid1_sources = lambda: [source_one, source_two]
                builder.run = lambda command, **_kwargs: commands.append(command) or types.SimpleNamespace()

                builder.build_init(
                    types.SimpleNamespace(
                        cross_gcc="aarch64-linux-gnu-gcc",
                        strip="aarch64-linux-gnu-strip",
                        init_binary=output_binary,
                    )
                )

                self.assertTrue(output_binary.parent.is_dir())
                self.assertEqual(
                    commands[0],
                    [
                        "aarch64-linux-gnu-gcc",
                        "-static",
                        "-Os",
                        "-Wall",
                        "-Wextra",
                        "-o",
                        output_binary,
                        source_one,
                        source_two,
                    ],
                )
                self.assertEqual(commands[1], ["aarch64-linux-gnu-strip", output_binary])
                self.assertEqual(commands[2], ["file", output_binary])
        finally:
            builder.pid1_sources = old_pid1_sources
            builder.run = old_run

    def test_build_ramdisk_copies_init_and_helpers_with_reproducible_cpio_command(self) -> None:
        old_helpers = builder.RAMDISK_HELPERS
        old_run = builder.run
        commands: list[tuple[list[str], Path | None]] = []
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                init_binary = root / "init_v724"
                init_binary.write_text("init", encoding="utf-8")
                helper_source = root / "a90_tcpctl"
                helper_source.write_text("helper", encoding="utf-8")
                stale_file = root / "ramdisk" / "stale"
                stale_file.parent.mkdir()
                stale_file.write_text("remove-me", encoding="utf-8")
                ramdisk_cpio = root / "out" / "ramdisk.cpio"
                ramdisk_cpio.parent.mkdir()
                ramdisk_cpio.write_text("old", encoding="utf-8")

                builder.RAMDISK_HELPERS = {"bin/a90_tcpctl": helper_source}
                builder.run = lambda command, *, cwd=None, **_kwargs: commands.append((command, cwd)) or types.SimpleNamespace()

                builder.build_ramdisk(
                    types.SimpleNamespace(
                        init_binary=init_binary,
                        ramdisk_dir=root / "ramdisk",
                        ramdisk_cpio=ramdisk_cpio,
                    )
                )

                self.assertFalse(stale_file.exists())
                self.assertEqual((root / "ramdisk" / "init").read_text(encoding="utf-8"), "init")
                self.assertEqual((root / "ramdisk" / "bin" / "a90_tcpctl").read_text(encoding="utf-8"), "helper")
                self.assertEqual((root / "ramdisk" / "init").stat().st_mode & 0o777, 0o755)
                self.assertEqual((root / "ramdisk" / "bin" / "a90_tcpctl").stat().st_mode & 0o777, 0o755)
                self.assertFalse(ramdisk_cpio.exists())
                self.assertEqual(commands[0][0][0:2], ["bash", "-lc"])
                self.assertEqual(commands[0][1], root / "ramdisk")
                self.assertIn("cpio --reproducible -o -H newc", commands[0][0][2])
                self.assertIn(str(ramdisk_cpio), commands[0][0][2])
        finally:
            builder.RAMDISK_HELPERS = old_helpers
            builder.run = old_run

    def test_build_boot_image_replaces_base_ramdisk_argument_and_rejects_missing_ramdisk_arg(self) -> None:
        old_run = builder.run
        commands: list[list[str | Path]] = []
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                ramdisk_cpio = root / "ramdisk.cpio"
                boot_image = root / "boot.img"
                boot_image.write_text("old", encoding="utf-8")

                def fake_run(command, *, capture=False, **_kwargs):
                    commands.append(command)
                    if capture:
                        return types.SimpleNamespace(
                            stdout="--kernel old-kernel --ramdisk old-ramdisk --cmdline old-cmdline"
                        )
                    return types.SimpleNamespace()

                builder.run = fake_run
                builder.build_boot_image(
                    types.SimpleNamespace(
                        base_boot=root / "base.img",
                        ramdisk_cpio=ramdisk_cpio,
                        boot_image=boot_image,
                    )
                )

                self.assertFalse(boot_image.exists())
                self.assertEqual(commands[1][0:2], ["python3", builder.MKBOOTIMG_DIR / "mkbootimg.py"])
                self.assertIn("--ramdisk", commands[1])
                self.assertEqual(commands[1][commands[1].index("--ramdisk") + 1], str(ramdisk_cpio))
                self.assertEqual(commands[1][-2:], ["--output", boot_image])

                builder.run = lambda command, *, capture=False, **_kwargs: types.SimpleNamespace(
                    stdout="--kernel old-kernel --cmdline old-cmdline"
                )
                with self.assertRaisesRegex(RuntimeError, "did not include --ramdisk"):
                    builder.build_boot_image(
                        types.SimpleNamespace(
                            base_boot=root / "base.img",
                            ramdisk_cpio=ramdisk_cpio,
                            boot_image=root / "boot2.img",
                        )
                    )
        finally:
            builder.run = old_run

    def test_verify_markers_accepts_complete_boot_strings_and_reports_missing_markers(self) -> None:
        old_run = builder.run
        try:
            boot_image = Path("boot.img")
            builder.run = lambda _command, *, capture=False, **_kwargs: types.SimpleNamespace(
                stdout="\n".join(builder.EXPECTED_MARKERS)
            )
            builder.verify_markers(types.SimpleNamespace(boot_image=boot_image))

            builder.run = lambda _command, *, capture=False, **_kwargs: types.SimpleNamespace(
                stdout=builder.EXPECTED_MARKERS[0]
            )
            with self.assertRaisesRegex(RuntimeError, "missing boot image markers"):
                builder.verify_markers(types.SimpleNamespace(boot_image=boot_image))
        finally:
            builder.run = old_run


if __name__ == "__main__":
    unittest.main()
