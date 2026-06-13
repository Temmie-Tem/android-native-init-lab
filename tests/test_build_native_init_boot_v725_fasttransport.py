"""Regression tests for build_native_init_boot_v725_fasttransport."""

from __future__ import annotations

import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v725_fasttransport")


class BuildNativeInitBootV725Fasttransport(unittest.TestCase):
    def test_pid1_sources_uses_arg_init_source_and_skips_a90_main_programs(self) -> None:
        old_linux_init = builder.LINUX_INIT
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                source_root = Path(temp_dir)
                init_source = source_root / "custom_init.c"
                init_source.write_text("void init_entry(void) {}\n", encoding="utf-8")
                library_source = source_root / "a90_netservice.c"
                library_source.write_text("void helper(void) {}\n", encoding="utf-8")
                standalone_source = source_root / "a90_cli.c"
                standalone_source.write_text("int main (int argc, char **argv) { return argc + !!argv; }\n", encoding="utf-8")

                builder.LINUX_INIT = source_root

                sources = builder.pid1_sources(types.SimpleNamespace(init_source=init_source))
        finally:
            builder.LINUX_INIT = old_linux_init

        self.assertEqual(sources[0], init_source)
        self.assertIn(library_source, sources)
        self.assertNotIn(standalone_source, sources)

    def test_build_init_injects_fasttransport_flags_before_output_and_sources(self) -> None:
        old_pid1_sources = builder.pid1_sources
        old_run = builder.run
        commands: list[list[str | Path]] = []
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                output_binary = root / "build" / "init_v725_fasttransport"
                source_one = root / "init_v725_fasttransport.c"
                source_two = root / "a90_netservice.c"
                args = types.SimpleNamespace(
                    cross_gcc="aarch64-linux-gnu-gcc",
                    strip="aarch64-linux-gnu-strip",
                    init_binary=output_binary,
                )
                builder.pid1_sources = lambda received_args: self.assertIs(received_args, args) or [
                    source_one,
                    source_two,
                ]
                builder.run = lambda command, **_kwargs: commands.append(command) or types.SimpleNamespace()

                builder.build_init(args)

                self.assertTrue(output_binary.parent.is_dir())
                compile_command = commands[0]
                self.assertEqual(compile_command[0:5], ["aarch64-linux-gnu-gcc", "-static", "-Os", "-Wall", "-Wextra"])
                for flag in builder.EXTRA_CFLAGS:
                    self.assertIn(flag, compile_command)
                    self.assertLess(compile_command.index(flag), compile_command.index("-o"))
                self.assertIn('-DNETSERVICE_USB_HELPER="/bin/a90_usbnet"', compile_command)
                self.assertIn('-DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl"', compile_command)
                self.assertIn('-DA90_BUSYBOX_HELPER="/bin/busybox"', compile_command)
                self.assertEqual(compile_command[compile_command.index("-o") + 1], output_binary)
                self.assertEqual(compile_command[-2:], [source_one, source_two])
                self.assertEqual(commands[1], ["aarch64-linux-gnu-strip", output_binary])
                self.assertEqual(commands[2], ["file", output_binary])
        finally:
            builder.pid1_sources = old_pid1_sources
            builder.run = old_run

    def test_build_ramdisk_materializes_transport_helpers_with_executable_modes(self) -> None:
        old_helpers = builder.RAMDISK_HELPERS
        old_run = builder.run
        commands: list[tuple[list[str], Path | None]] = []
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                init_binary = root / "init_v725_fasttransport"
                init_binary.write_text("init", encoding="utf-8")
                helper_sources = {
                    "bin/a90_tcpctl": root / "a90_tcpctl",
                    "bin/a90_usbnet": root / "a90_usbnet",
                    "bin/busybox": root / "busybox",
                    "bin/toybox": root / "toybox",
                }
                for relative, source in helper_sources.items():
                    source.write_text(f"{relative}\n", encoding="utf-8")
                ramdisk_cpio = root / "out" / "ramdisk.cpio"
                ramdisk_cpio.parent.mkdir()
                ramdisk_cpio.write_text("old", encoding="utf-8")

                builder.RAMDISK_HELPERS = helper_sources
                builder.run = lambda command, *, cwd=None, **_kwargs: commands.append((command, cwd)) or types.SimpleNamespace()

                builder.build_ramdisk(
                    types.SimpleNamespace(
                        init_binary=init_binary,
                        ramdisk_dir=root / "ramdisk",
                        ramdisk_cpio=ramdisk_cpio,
                    )
                )

                self.assertEqual((root / "ramdisk" / "init").read_text(encoding="utf-8"), "init")
                for relative in helper_sources:
                    destination = root / "ramdisk" / relative
                    self.assertEqual(destination.read_text(encoding="utf-8"), f"{relative}\n")
                    self.assertEqual(destination.stat().st_mode & 0o777, 0o755)
                self.assertFalse(ramdisk_cpio.exists())
                self.assertEqual(commands[0][0][0:2], ["bash", "-lc"])
                self.assertEqual(commands[0][1], root / "ramdisk")
                self.assertIn("LC_ALL=C sort", commands[0][0][2])
                self.assertIn("cpio --reproducible -o -H newc", commands[0][0][2])
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
                self.assertEqual(commands[0][0:2], ["python3", builder.MKBOOTIMG_DIR / "unpack_bootimg.py"])
                self.assertEqual(commands[1][0:2], ["python3", builder.MKBOOTIMG_DIR / "mkbootimg.py"])
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

    def test_verify_markers_accepts_fasttransport_markers_and_reports_missing_marker(self) -> None:
        old_run = builder.run
        try:
            boot_image = Path("boot.img")
            builder.run = lambda _command, *, capture=False, **_kwargs: types.SimpleNamespace(
                stdout="\n".join(builder.EXPECTED_MARKERS)
            )
            builder.verify_markers(types.SimpleNamespace(boot_image=boot_image))

            partial_markers = "\n".join(marker for marker in builder.EXPECTED_MARKERS if marker != "/bin/a90_usbnet")
            builder.run = lambda _command, *, capture=False, **_kwargs: types.SimpleNamespace(stdout=partial_markers)
            with self.assertRaisesRegex(RuntimeError, "/bin/a90_usbnet"):
                builder.verify_markers(types.SimpleNamespace(boot_image=boot_image))
        finally:
            builder.run = old_run


if __name__ == "__main__":
    unittest.main()
