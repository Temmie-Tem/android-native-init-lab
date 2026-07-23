import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"


def load_module(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_tested", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P234CandidateStaticCheckerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        cls.module = load_module("s22plus_fyg8_p234_candidate_static_checker")

    def test_candidate_cli_help_exits_cleanly(self):
        with self.assertRaises(SystemExit) as context:
            self.module.candidate.main(["--help"])
        self.assertEqual(context.exception.code, 0)

    def fixture(self):
        exact_contract = {"run_id": "12" * 16, "profile": "E1A"}
        outputs = {
            "boot_img": {"size": 10, "sha256": "1" * 64},
            "boot_img_lz4": {"size": 11, "sha256": "2" * 64},
            "ap_tar_md5": {"size": 12, "sha256": "3" * 64},
        }
        image = {"size": 13, "sha256": "4" * 64}
        repro = {"size": 14, "sha256": "5" * 64}
        userspace = {
            "result": {"size": 15, "sha256": "6" * 64},
            "init": {"size": 16, "sha256": "7" * 64},
            "child": {"size": 17, "sha256": "8" * 64},
            "two_build_byte_identical": True,
            "verified": True,
        }
        result = {
            "schema": self.module.candidate.SCHEMA,
            "target": self.module.TARGET,
            "verdict": self.module.candidate.VERDICT,
            "candidate_contract": exact_contract,
            "kernel_closure": {
                "result": repro,
                "image": image,
                "two_clean_builds_byte_identical": True,
                "linked_audit_verified": True,
            },
            "userspace_closure": userspace,
            "construction": {
                "header_preserved": True,
                "ramdisk_preserved": True,
                "kernel_exact_image": True,
                "magiskboot_nochange_byte_identical": True,
                "base_child_absent": True,
                "patch_vbmeta_flag": False,
                "outside_interval_changed_byte_count": 0,
                "kernel_interval": [
                    self.module.candidate.KERNEL_START,
                    self.module.candidate.KERNEL_END,
                ],
            },
            "outputs": {**outputs, "ap_structure": {"members": ["boot.img.lz4"]}},
            "manifest_created": False,
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "boot_only_ap": True,
                "ap_members": ["boot.img.lz4"],
                "no_shell": True,
                "no_usb_or_configfs": True,
                "no_block_write": True,
                "no_reboot_syscall": True,
            },
        }
        inputs = {
            "exact_contract": exact_contract,
            "outputs": outputs,
            "image_receipt": image,
            "repro_receipt": repro,
            "userspace_closure": userspace,
        }
        return result, inputs

    def test_artifact_result_exact_contract_passes(self):
        result, inputs = self.fixture()
        self.assertTrue(
            self.module.verify_artifact_result(result, **inputs)["verified"]
        )

    def test_artifact_result_rejects_extra_ap_member(self):
        result, inputs = self.fixture()
        result["outputs"]["ap_structure"]["members"].append("recovery.img.lz4")
        with self.assertRaisesRegex(self.module.CheckError, "boot-only"):
            self.module.verify_artifact_result(result, **inputs)

    def test_artifact_result_rejects_changed_repro_receipt(self):
        result, inputs = self.fixture()
        changed = copy.deepcopy(inputs)
        changed["repro_receipt"]["sha256"] = "9" * 64
        with self.assertRaisesRegex(self.module.CheckError, "kernel closure"):
            self.module.verify_artifact_result(result, **changed)

    def test_artifact_result_rejects_weakened_safety(self):
        result, inputs = self.fixture()
        result["safety"]["device_contact"] = True
        with self.assertRaisesRegex(self.module.CheckError, "safety"):
            self.module.verify_artifact_result(result, **inputs)

    def test_e1b_artifact_requires_stock_module_reuse_without_injection(self):
        result, inputs = self.fixture()
        inputs["exact_contract"]["profile"] = "E1B"
        result["candidate_contract"]["profile"] = "E1B"
        result["module_closure"] = {
            "files": [spec["file"] for spec in self.module.carrier.MODULE_SPECS],
            "runtime_names": [
                spec["runtime"] for spec in self.module.carrier.MODULE_SPECS
            ],
            "count": len(self.module.carrier.MODULE_SPECS),
        }
        result["construction"].update(
            {
                "module_binaries_injected": 0,
                "vendor_ramdisk_modules_reused": True,
            }
        )
        self.assertTrue(
            self.module.verify_artifact_result(result, **inputs)["verified"]
        )
        result["construction"]["module_binaries_injected"] = 1
        with self.assertRaisesRegex(self.module.CheckError, "module closure"):
            self.module.verify_artifact_result(result, **inputs)

    def test_e2_artifact_requires_exact_59_module_closure_and_scoped_safety(self):
        required = (
            self.module.e2_closure.DEFAULT_VENDOR_RAMDISK,
            self.module.e2_closure.DEFAULT_LZ4,
        )
        if not all((ROOT / path).exists() for path in required):
            self.skipTest("exact FYG8 private inputs are unavailable")
        closure = self.module.e2_closure.derive_module_closure(
            ROOT,
            ROOT / self.module.e2_closure.DEFAULT_VENDOR_RAMDISK,
            ROOT / self.module.e2_closure.DEFAULT_LZ4,
        )
        result, inputs = self.fixture()
        inputs["exact_contract"]["profile"] = "E2"
        result["candidate_contract"]["profile"] = "E2"
        result["module_closure"] = closure
        result["construction"].update(
            {
                "module_binaries_injected": 0,
                "vendor_ramdisk_modules_reused": True,
            }
        )
        result["safety"].pop("no_usb_or_configfs")
        result["safety"].update(
            {
                "no_userspace_sysfs_or_configfs_write": True,
                "usb_scope": "active-module-init-probe-and-read-only-bind-gates",
                "module_init_probe_authority": "active-live-unproved",
            }
        )
        self.assertTrue(
            self.module.verify_artifact_result(result, **inputs)["verified"]
        )
        result["module_closure"]["modules"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(self.module.CheckError, "module closure"):
            self.module.verify_artifact_result(result, **inputs)

    def test_stable_read_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            direct = root / "direct"
            direct.write_bytes(b"data")
            indirect = root / "indirect"
            indirect.symlink_to(direct)
            with self.assertRaises(OSError):
                self.module.stable_read(indirect, "indirect", 16)

    def test_critical_storage_rejects_hardlinks(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            first = root / "first"
            second = root / "second"
            first.write_bytes(b"candidate")
            second.hardlink_to(first)
            with self.assertRaisesRegex(
                self.module.CheckError, "unique regular storage"
            ):
                self.module.require_unique_regular_storage([first, second])

    def test_critical_storage_accepts_distinct_regular_files(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            first = root / "first"
            second = root / "second"
            first.write_bytes(b"candidate-a")
            second.write_bytes(b"candidate-b")
            self.module.require_unique_regular_storage([first, second])

    def test_package_repro_defaults_are_distinct(self):
        self.assertNotEqual(
            self.module.DEFAULT_CANDIDATE, self.module.DEFAULT_CANDIDATE_B
        )


if __name__ == "__main__":
    unittest.main()
