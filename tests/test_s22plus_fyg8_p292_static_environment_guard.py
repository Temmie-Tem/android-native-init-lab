from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from workspace.public.src.scripts.revalidation import (
    s22plus_fyg8_p292_static_environment_guard as guard,
)


class P292StaticEnvironmentGuardTest(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict[str, str]]:
        tool_bin = root / "tools"
        tool_bin.mkdir()
        for name in guard.EXPECTED_TOOL_NAMES:
            target = tool_bin / name
            target.write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
            target.chmod(0o700)
        return tool_bin, {"PATH": str(tool_bin), "LD_LIBRARY_PATH": str(root)}

    def test_source_derived_userspace_inventory_is_exact(self) -> None:
        self.assertEqual(
            tuple(guard.userspace.base.TOOL_NAMES),
            guard.EXPECTED_USERSPACE_TOOL_NAMES,
        )

    def test_exact_basename_inventory_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tool_bin, environment = self.fixture(root)
            rows = guard.resolve_tools(tool_bin, environment)
            self.assertEqual(set(rows), set(guard.EXPECTED_TOOL_NAMES))

    def test_missing_nested_basename_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tool_bin, environment = self.fixture(root)
            (tool_bin / "aarch64-linux-gnu-nm").unlink()
            with self.assertRaisesRegex(guard.EnvironmentGuardError, "basename is missing"):
                guard.resolve_tools(tool_bin, environment)

    def test_pinned_basename_escape_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tool_bin, environment = self.fixture(root)
            target = tool_bin / "aarch64-linux-gnu-nm"
            target.unlink()
            target.symlink_to("/bin/true")
            with self.assertRaisesRegex(guard.EnvironmentGuardError, "escaped"):
                guard.resolve_tools(tool_bin, environment)

    def test_baseline_receipt_mismatch_fails(self) -> None:
        rows = {
            name: {"size": 1, "sha256": hashlib.sha256(name.encode()).hexdigest()}
            for name in guard.EXPECTED_TOOL_NAMES
        }
        postbuild = {
            "linked_audit": {
                "staged_input_receipts": {
                    "nm": {"size": 2, "sha256": "0" * 64},
                    "objdump": {
                        "size": rows["aarch64-linux-gnu-objdump"]["size"],
                        "sha256": rows["aarch64-linux-gnu-objdump"]["sha256"],
                    },
                },
                "postbuild_audit": {
                    "host_native_exhaustive": {
                        "compiler": {
                            "size": rows["cc"]["size"],
                            "sha256": rows["cc"]["sha256"],
                        }
                    }
                },
            }
        }
        static = {
            "tools": {
                "qemu_aarch64": {
                    "size": rows["qemu-aarch64"]["size"],
                    "sha256": rows["qemu-aarch64"]["sha256"],
                }
            }
        }
        with self.assertRaisesRegex(guard.EnvironmentGuardError, "differs from baseline"):
            guard.require_baseline_receipts(rows, postbuild, static)


if __name__ == "__main__":
    unittest.main()
