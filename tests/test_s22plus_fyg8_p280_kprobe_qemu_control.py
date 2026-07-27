from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p280_kprobe_qemu_control.py"
)
SOURCE = (
    REPO
    / "workspace/public/src/native-init/"
    "s22plus_fyg8_p280_kprobe_qemu_control.c"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "p280_kprobe_qemu_control", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8P280KprobeQemuControlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_current_source_passes(self) -> None:
        self.module.verify_source(SOURCE.read_bytes())

    def test_required_guest_config_passes(self) -> None:
        data = ("\n".join(self.module.REQUIRED_CONFIG) + "\n").encode("ascii")
        self.module.verify_guest_config(data)

    def test_missing_kretprobe_config_fails(self) -> None:
        values = [
            value
            for value in self.module.REQUIRED_CONFIG
            if value != "CONFIG_KRETPROBES=y"
        ]
        with self.assertRaisesRegex(
            self.module.HarnessError, "CONFIG_KRETPROBES"
        ):
            self.module.verify_guest_config(
                ("\n".join(values) + "\n").encode("ascii")
            )

    def test_return_probe_mutation_fails(self) -> None:
        mutated = SOURCE.read_bytes().replace(
            b'" rc=$retval:s32\\n"',
            b'" rc=$retval:u64\\n"',
            1,
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "token cardinality"
        ):
            self.module.verify_source(mutated)

    def test_cleanup_mutation_fails(self) -> None:
        mutated = SOURCE.read_bytes().replace(
            b"umount(P280_TRACE_ROOT)",
            b"umount(\"/wrong\")",
            1,
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "missing"
        ):
            self.module.verify_source(mutated)

    def test_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact"
            path.write_bytes(b"wrong")
            with self.assertRaisesRegex(
                self.module.HarnessError, "SHA256 mismatch"
            ):
                self.module.require_sha256(
                    path,
                    "0" * 64,
                    "fixture",
                )

    def test_host_command_timeout_fails_closed(self) -> None:
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["fixture"], 1),
        ):
            with self.assertRaisesRegex(
                self.module.HarnessError, "command timed out: fixture"
            ):
                self.module._run(["fixture"])

    def test_qemu_version_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            self.module.HarnessError, "QEMU version mismatch"
        ):
            self.module.verify_qemu_version_result(
                0,
                "QEMU emulator version 0.0.0\n",
            )

    def test_exact_qemu_version_passes(self) -> None:
        self.assertEqual(
            self.module.verify_qemu_version_result(
                0,
                self.module.PINNED_QEMU_VERSION + "\n",
            ),
            self.module.PINNED_QEMU_VERSION,
        )

    def test_qemu_version_query_timeout_fails_closed(self) -> None:
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["qemu", "--version"], 10),
        ):
            with self.assertRaisesRegex(
                self.module.HarnessError, "QEMU version query timed out"
            ):
                self.module.query_qemu_version(Path("/qemu"), {})

    def test_cpio_timeout_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(
                self.module.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["cpio"], 1),
            ):
                with self.assertRaisesRegex(
                    self.module.HarnessError, "cpio timed out"
                ):
                    self.module.build_cpio(root, root / "initramfs.cpio")


if __name__ == "__main__":
    unittest.main()
