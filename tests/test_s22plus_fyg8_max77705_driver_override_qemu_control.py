from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_driver_override_qemu_control.py"
)
SOURCE = (
    ROOT
    / "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_driver_override_qemu_control.c"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "max77705_driver_override_qemu", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Max77705DriverOverrideQemuControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.source = SOURCE.read_bytes()

    def test_current_source_contract_passes(self) -> None:
        self.module.verify_source(self.source)

    def test_override_after_driver_registration_rejects(self) -> None:
        first = self.source.find(
            b"\tcontrol_set_override(active.names[1], CONTROL_OVERRIDE"
        )
        second_load = self.source.find(b"\tcontrol_load_module();", first)
        self.assertGreaterEqual(first, 0)
        self.assertGreater(second_load, first)
        line_end = self.source.find(b"\n", second_load) + 1
        load_line = self.source[second_load:line_end]
        mutated = (
            self.source[:first]
            + load_line
            + self.source[first:second_load]
            + self.source[line_end:]
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "proof order"
        ):
            self.module.verify_source(mutated)

    def test_missing_second_blocker_rejects(self) -> None:
        mutated = self.source.replace(
            b"\tcontrol_set_override(active.names[2], CONTROL_OVERRIDE \"\\n\");\n",
            b"",
            1,
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "proof order"
        ):
            self.module.verify_source(mutated)

    def test_direct_bind_or_unbind_shortcut_rejects(self) -> None:
        marker = b"int main(void)\n{"
        mutated = self.source.replace(
            marker,
            marker + b'\n\tconst char *forbidden = "/unbind";',
            1,
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "forbidden shortcut"
        ):
            self.module.verify_source(mutated)

    def test_guest_config_requires_module_unload_and_virtio_mmio(self) -> None:
        valid = "\n".join(self.module.REQUIRED_CONFIG).encode("ascii") + b"\n"
        self.module.verify_guest_config(valid)
        for removed in (b"CONFIG_MODULE_UNLOAD=y\n", b"CONFIG_VIRTIO_MMIO=m\n"):
            with self.subTest(removed=removed), self.assertRaisesRegex(
                self.module.HarnessError, "lacks required"
            ):
                self.module.verify_guest_config(valid.replace(removed, b""))

    def test_pass_line_requires_three_unique_platform_devices(self) -> None:
        result = self.module.parse_pass_line(
            "MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            "target=a.virtio_mmio blocked=b.virtio_mmio,c.virtio_mmio active=3\r\n"
        )
        self.assertEqual(result["active_count"], 3)
        self.assertEqual(result["blocked"], ["b.virtio_mmio", "c.virtio_mmio"])
        bad = (
            "MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            "target=a.virtio_mmio blocked=a.virtio_mmio,c.virtio_mmio active=3\n"
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "invalid device cardinality"
        ):
            self.module.parse_pass_line(bad)

    def test_partial_terminal_marker_does_not_stop_observer(self) -> None:
        marker = b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
        partial = marker + b"target=a.virtio_mmio active=3"
        self.assertFalse(self.module.complete_record_seen(partial, marker))
        self.assertTrue(self.module.complete_record_seen(partial + b"\n", marker))

    def test_qemu_version_is_exact(self) -> None:
        self.assertEqual(
            self.module.verify_qemu_version_result(
                0, self.module.PINNED_QEMU_VERSION + "\n"
            ),
            self.module.PINNED_QEMU_VERSION,
        )
        with self.assertRaisesRegex(self.module.HarnessError, "version mismatch"):
            self.module.verify_qemu_version_result(0, "QEMU wrong\n")


if __name__ == "__main__":
    unittest.main()
