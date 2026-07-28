from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_p282_classifier_qemu.py"
CLASSIFIER = (
    REPO
    / "workspace/public/src/native-init/"
    "s22plus_fyg8_p282_classifier.inc.c"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "p282_classifier_qemu",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8P282ClassifierQemuTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def _pass_report(self) -> dict[str, object]:
        receipt = {
            "path": "/pinned",
            "sha256": "1" * 64,
            "version": "pinned-version",
        }
        return {
            "schema": self.module.SCHEMA,
            "verdict": self.module.VERDICT,
            "details_covered": 46,
            "tuple_count": 567,
            "elapsed_sec": 1.0,
            "command": ["/qemu", "-nic", "none"],
            "substrate": {
                "kernel": dict(receipt),
                "config": dict(receipt),
                "qemu": dict(receipt),
                "compiler": dict(receipt),
            },
            "production_classifier_sha256": "2" * 64,
            "contract_spec_sha256": "3" * 64,
            "generated_contract_sha256": "4" * 64,
            "guest_source_sha256": "5" * 64,
            "init_sha256": "6" * 64,
            "initramfs_sha256": "7" * 64,
            "qemu_output_sha256": "8" * 64,
            "scope": {"validated": [], "not_validated": []},
        }

    def test_current_production_classifier_passes_source_gate(self) -> None:
        self.module.verify_classifier_source(CLASSIFIER.read_bytes())

    def test_tuple_formula_mutation_fails_closed(self) -> None:
        mutated = CLASSIFIER.read_bytes().replace(
            b"P282_STATE_COUNT + state",
            b"P282_STATE_COUNT - state",
            1,
        )
        with self.assertRaisesRegex(
            self.module.HarnessError,
            "semantic token missing",
        ):
            self.module.verify_classifier_source(mutated)

    def test_classifier_test_hook_mutation_fails_closed(self) -> None:
        mutated = CLASSIFIER.read_bytes() + b"\n#ifdef TEST\n#endif\n"
        with self.assertRaisesRegex(
            self.module.HarnessError,
            "test hook",
        ):
            self.module.verify_classifier_source(mutated)

    def test_guest_source_executes_exact_domains(self) -> None:
        source = self.module.render_guest_source("a" * 64)
        self.assertEqual(source.count("return 1002;"), 1)
        self.assertIn("details_covered=46", source)
        self.assertIn("tuple_count=567", source)
        self.assertIn("p282_classify_final_pair(", source)
        self.assertIn("p282_encode_tuple(", source)
        for fixture in self.module.contract_spec.CLASSIFIER_FIXTURES:
            self.assertIn(f"0x{fixture.detail:03x}U", source)

    def test_qemu_command_is_networkless_and_pinned_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "usr/bin/qemu-system-aarch64"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"qemu")
            build = {
                "kernel": "/guest/vmlinuz",
                "initramfs": "/guest/initramfs.cpio",
            }
            with (
                mock.patch.object(
                    self.module,
                    "require_sha256",
                    return_value=self.module.PINNED_QEMU_SHA256,
                ),
                mock.patch.object(
                    self.module,
                    "query_qemu_version",
                    return_value=self.module.PINNED_QEMU_VERSION,
                ),
            ):
                command, _, identity = self.module._qemu_command(
                    qemu_root=root,
                    build=build,
                )
        self.assertEqual(command[command.index("-nic") + 1], "none")
        self.assertNotIn("-netdev", command)
        self.assertEqual(command[command.index("-kernel") + 1], build["kernel"])
        self.assertEqual(
            command[command.index("-initrd") + 1],
            build["initramfs"],
        )
        self.assertEqual(identity["sha256"], self.module.PINNED_QEMU_SHA256)
        self.assertEqual(identity["version"], self.module.PINNED_QEMU_VERSION)

    def test_substrate_pins_are_reused_from_p280_control(self) -> None:
        p280 = self.module.p280_qemu
        self.assertEqual(self.module.KERNEL_VERSION, p280.KERNEL_VERSION)
        self.assertEqual(
            self.module.PINNED_KERNEL_SHA256,
            p280.PINNED_KERNEL_SHA256,
        )
        self.assertEqual(
            self.module.PINNED_CONFIG_SHA256,
            p280.PINNED_CONFIG_SHA256,
        )
        self.assertEqual(
            self.module.PINNED_QEMU_SHA256,
            p280.PINNED_QEMU_SHA256,
        )
        self.assertEqual(
            self.module.PINNED_QEMU_VERSION,
            p280.PINNED_QEMU_VERSION,
        )

    def test_result_schema_accepts_exact_pass(self) -> None:
        self.module.validate_result_schema(self._pass_report())

    def test_result_schema_rejects_coverage_mutation(self) -> None:
        report = self._pass_report()
        report["details_covered"] = 45
        with self.assertRaisesRegex(
            self.module.HarnessError,
            "incomplete classifier coverage",
        ):
            self.module.validate_result_schema(report)

    def test_result_schema_rejects_extra_key(self) -> None:
        report = self._pass_report()
        report["unexpected"] = True
        with self.assertRaisesRegex(
            self.module.HarnessError,
            "exact schema",
        ):
            self.module.validate_result_schema(report)

    def test_exact_pass_marker_and_sha_are_required(self) -> None:
        marker = (
            b"P282_CLASSIFIER_QEMU result=PASS "
            b"details_covered=46 tuple_count=567 "
            b"classifier_sha=" + b"a" * 64 + b"\n"
        )
        self.assertEqual(
            self.module.parse_guest_result(marker, "a" * 64),
            (self.module.VERDICT, 46, 567),
        )
        with self.assertRaisesRegex(
            self.module.HarnessError,
            "does not match",
        ):
            self.module.parse_guest_result(marker, "b" * 64)

    def test_guest_failure_marker_cannot_claim_coverage(self) -> None:
        self.assertEqual(
            self.module.parse_guest_result(
                b"P282_CLASSIFIER_QEMU result=FAIL code=19\n",
                "a" * 64,
            ),
            (self.module.FAIL_VERDICT, 0, 0),
        )

    def test_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact"
            path.write_bytes(b"wrong")
            with self.assertRaisesRegex(
                self.module.HarnessError,
                "SHA256 mismatch",
            ):
                self.module.require_sha256(path, "0" * 64, "artifact")

    def test_qemu_version_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            self.module.HarnessError,
            "QEMU version mismatch",
        ):
            self.module.verify_qemu_version_result(
                0,
                "QEMU emulator version 0.0.0\n",
            )

    def test_host_command_timeout_fails_closed(self) -> None:
        with mock.patch.object(
            self.module.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["fixture"], 1),
        ):
            with self.assertRaisesRegex(
                self.module.HarnessError,
                "command timed out",
            ):
                self.module._run(["fixture"])


if __name__ == "__main__":
    unittest.main()
