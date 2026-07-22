import hashlib
import importlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class P221ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = importlib.import_module(
            "s22plus_fyg8_p221_build_artifact_contract"
        )
        cls.builder = importlib.import_module("build_s22plus_fyg8_p221_candidate")
        cls.checker = importlib.import_module(
            "s22plus_fyg8_p221_candidate_static_checker"
        )

    @staticmethod
    def receipt(data):
        return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def fixture(self):
        image = b"image"
        vmlinux = b"vmlinux"
        config = (self.artifact.CONFIG_SYMBOL + "\n").encode()
        result = {
            "schema": self.artifact.BUILD_SCHEMA,
            "target": self.artifact.TARGET,
            "mode": "build",
            "returncode": 0,
            "p221_build_pass": True,
            "p219_same_ring_contract": {"verdict": self.artifact.BUILD_VERDICT},
            "source_delta": {
                "patch_sha256": self.artifact.PATCH_SHA256,
                "restored": True,
            },
            "outputs": [
                {"name": "Image", **self.receipt(image)},
                {"name": "vmlinux", **self.receipt(vmlinux)},
                {"name": ".config", **self.receipt(config)},
            ],
            "safety": {
                "host_only": True,
                "device_contact": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "packaging_outputs_promoted": False,
            },
        }
        for name in (
            "source_symlink_control_runtime",
            "output_gate",
            "module_gate",
            "kernel_banner_gate",
            "witness_output_gate",
            "sec_log_buf_timing_gate",
            "exclusive_output_root",
        ):
            result[name] = {"verified": True}
        encoded = json.dumps(result, sort_keys=True).encode()
        return image, vmlinux, config, encoded

    def bind_fixture(self, image, vmlinux, config, result):
        values = {
            "IMAGE_SIZE": len(image),
            "IMAGE_SHA256": self.receipt(image)["sha256"],
            "VMLINUX_SIZE": len(vmlinux),
            "VMLINUX_SHA256": self.receipt(vmlinux)["sha256"],
            "CONFIG_SIZE": len(config),
            "CONFIG_SHA256": self.receipt(config)["sha256"],
            "BUILD_RESULT_SIZE": len(result),
            "BUILD_RESULT_SHA256": self.receipt(result)["sha256"],
        }
        return mock.patch.multiple(self.artifact, **values)

    def test_build_artifact_contract_accepts_exact_closure(self):
        image, vmlinux, config, result = self.fixture()
        with self.bind_fixture(image, vmlinux, config, result):
            checked = self.artifact.verify(
                image=image, vmlinux=vmlinux, config=config, build_result=result
            )
        self.assertTrue(checked["verified"])
        self.assertEqual(checked["compiled_config_symbol_count"], 1)

    def test_build_artifact_contract_rejects_any_mutation(self):
        image, vmlinux, config, result = self.fixture()
        with self.bind_fixture(image, vmlinux, config, result):
            with self.assertRaises(self.artifact.ArtifactError):
                self.artifact.verify(
                    image=image + b"x",
                    vmlinux=vmlinux,
                    config=config,
                    build_result=result,
                )

    def test_kernel_replacement_changes_only_fixed_interval(self):
        carrier = b"AAAAccccRRRRzzzz"
        image = b"IIII"

        def parse(value):
            return SimpleNamespace(
                header={"fixed": True}, ramdisk=value[8:12], kernel=value[4:8]
            )

        with mock.patch.multiple(
            self.builder, BOOT_SIZE=16, KERNEL_START=4, KERNEL_END=8
        ), mock.patch.object(self.builder.boot_verify, "parse_boot_v4", side_effect=parse):
            replaced, evidence = self.builder.replace_kernel(carrier, image)
        self.assertEqual(replaced, b"AAAAIIIIRRRRzzzz")
        self.assertTrue(evidence["header_preserved"])
        self.assertTrue(evidence["ramdisk_preserved"])
        self.assertEqual(evidence["outside_interval_changed_byte_count"], 0)

    def test_static_checker_reconstructs_interval_separately(self):
        carrier = b"AAAAccccRRRRzzzz"
        image = b"IIII"
        submitted = b"AAAAIIIIRRRRzzzz"

        def parse(value):
            return SimpleNamespace(
                header={"fixed": True}, ramdisk=value[8:12], kernel=value[4:8]
            )

        with mock.patch.multiple(
            self.checker.candidate,
            BOOT_SIZE=16,
            KERNEL_START=4,
            KERNEL_END=8,
        ), mock.patch.object(self.checker.boot_verify, "parse_boot_v4", side_effect=parse):
            evidence = self.checker.verify_fixed_interval(carrier, image, submitted)
            with self.assertRaises(self.checker.CheckError):
                self.checker.verify_fixed_interval(carrier, image, submitted[:-1] + b"x")
        self.assertTrue(evidence["verified"])

    def test_pinned_runtime_excludes_ring_writer(self):
        result = self.checker.verify_writer_exclusion(ROOT)
        self.assertTrue(result["verified"])
        self.assertFalse(result["sec_log_buf_loaded"])
        self.assertEqual(
            result["loaded_modules"],
            [row[0] for row in self.checker.e1.MODULE_SPECS],
        )

    def test_artifact_result_cannot_claim_manifest_or_live_authority(self):
        base = {
            "schema": self.builder.SCHEMA,
            "target": self.artifact.TARGET,
            "verdict": self.builder.VERDICT,
            "manifest_created": False,
            "outputs": {},
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
            },
        }
        self.assertFalse(
            self.checker._parse_result(json.dumps(base).encode())["manifest_created"]
        )
        base["safety"]["live_authorized"] = True
        with self.assertRaises(self.checker.CheckError):
            self.checker._parse_result(json.dumps(base).encode())


if __name__ == "__main__":
    unittest.main()
