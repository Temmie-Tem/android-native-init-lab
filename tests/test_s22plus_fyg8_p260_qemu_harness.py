from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p260_qemu_harness.py"
)
RUNTIME = (
    REPO
    / "workspace/public/src/native-init/"
    "s22plus_fyg8_p260_e3_runtime.inc.c"
)
HARNESS = (
    REPO
    / "workspace/public/src/native-init/"
    "s22plus_fyg8_p260_qemu_harness.c"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p260_qemu_harness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8P260QemuHarnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_current_runtime_and_harness_pass(self) -> None:
        self.module.verify_runtime_source(RUNTIME.read_bytes())
        self.module.verify_harness_source(HARNESS.read_bytes())

    def test_sysfs_magic_mutation_fails(self) -> None:
        mutated = RUNTIME.read_bytes().replace(
            b"0x62656570L", b"0x62656572L"
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "configfs magic"
        ):
            self.module.verify_runtime_source(mutated)

    def test_prebind_banner_order_mutation_fails(self) -> None:
        source = HARNESS.read_bytes()
        banner = source.find(b"    rc = p260_write_all(")
        bind = source.find(b"    rc = p260_write_and_verify(")
        self.assertGreaterEqual(banner, 0)
        self.assertGreater(bind, banner)
        banner_end = source.find(b"    qemu_log_stage(", banner)
        banner_end = source.find(b"\n", source.find(b");", banner_end)) + 1
        bind_end = source.find(b"    qemu_log_stage(", bind)
        bind_end = source.find(b"\n", source.find(b");", bind_end)) + 1
        banner_block = source[banner:banner_end]
        bind_block = source[bind:bind_end]
        mutated = (
            source[:banner]
            + bind_block
            + source[banner_end:bind]
            + banner_block
            + source[bind_end:]
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "before UDC bind"
        ):
            self.module.verify_harness_source(mutated)


if __name__ == "__main__":
    unittest.main()
