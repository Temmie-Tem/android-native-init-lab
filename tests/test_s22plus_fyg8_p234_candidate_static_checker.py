import copy
import importlib.util
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


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

    def test_p260_artifact_requires_bounded_write_safety(self):
        required = (
            self.module.e2_closure.DEFAULT_VENDOR_RAMDISK,
            self.module.e2_closure.DEFAULT_LZ4,
        )
        if not all((ROOT / path).exists() for path in required):
            self.skipTest("exact FYG8 private inputs are unavailable")
        result, inputs = self.fixture()
        exact_contract = inputs["exact_contract"]
        exact_contract.update(
            {
                "profile": "E2",
                "source_contract_id": (
                    self.module.candidate.P260_SOURCE_CONTRACT_ID
                ),
            }
        )
        result["candidate_contract"] = exact_contract
        result["module_closure"] = (
            self.module.e2_closure_selector.select(
                exact_contract["source_contract_id"]
            ).derive_module_closure(
                ROOT,
                ROOT / self.module.e2_closure.DEFAULT_VENDOR_RAMDISK,
                ROOT / self.module.e2_closure.DEFAULT_LZ4,
            )
        )
        result["construction"].update(
            {
                "module_binaries_injected": 0,
                "vendor_ramdisk_modules_reused": True,
            }
        )
        result["safety"] = {
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
            "no_block_write": True,
            "no_reboot_syscall": True,
            "userspace_sysfs_configfs_write_scope": (
                "source-contract-bound-p260-e3-acm-and-peripheral-role"
            ),
            "usb_scope": (
                "bounded-configfs-cdc-acm-banner-and-peripheral-role"
            ),
            "module_init_probe_authority": "active-live-unproved",
        }
        self.assertTrue(
            self.module.verify_artifact_result(result, **inputs)["verified"]
        )

        expected = result["safety"]
        for key in tuple(expected):
            with self.subTest(key=key):
                result["safety"] = copy.deepcopy(expected)
                result["safety"][key] = (
                    not result["safety"][key]
                    if isinstance(result["safety"][key], bool)
                    else "changed"
                )
                with self.assertRaisesRegex(self.module.CheckError, "safety"):
                    self.module.verify_artifact_result(result, **inputs)
        result["safety"] = {
            **expected,
            "no_userspace_sysfs_or_configfs_write": True,
        }
        with self.assertRaisesRegex(self.module.CheckError, "safety"):
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

    def test_verify_repro_selects_registered_adapter(self):
        source_contract_id = "test-static-adapter-contract"
        adapter_name = "test_static_repro_adapter"
        exact_contract = {
            "run_id": "12" * 16,
            "profile": "E2",
            "source_contract_id": source_contract_id,
        }
        fresh = {"candidate_contract": exact_contract, "verified": True}
        encoded = (self.module.json.dumps(fresh) + "\n").encode()
        adapter = types.SimpleNamespace(
            EXPECTED_SOURCE_CONTRACT_ID=source_contract_id,
            check=lambda _args: fresh,
        )
        original_read_json = self.module.read_json
        original_repro_check = self.module.repro.check
        self.module.repro.LINKED_VALIDATOR_ADAPTERS[source_contract_id] = adapter_name
        sys.modules[adapter_name] = adapter
        self.module.read_json = lambda *_args: (fresh, encoded)
        self.module.repro.check = lambda _args: self.fail(
            "registered adapter was bypassed"
        )
        try:
            result, result_receipt = self.module.verify_repro(
                ROOT, self.module.parse_args([]), exact_contract
            )
        finally:
            self.module.read_json = original_read_json
            self.module.repro.check = original_repro_check
            self.module.repro.LINKED_VALIDATOR_ADAPTERS.pop(
                source_contract_id, None
            )
            sys.modules.pop(adapter_name, None)
        self.assertEqual(result, fresh)
        self.assertEqual(result_receipt, self.module.receipt(encoded))

    def test_verify_repro_rejects_mismatched_adapter_contract(self):
        source_contract_id = "test-static-adapter-contract"
        adapter_name = "test_static_repro_adapter"
        exact_contract = {
            "run_id": "12" * 16,
            "profile": "E2",
            "source_contract_id": source_contract_id,
        }
        fresh = {"candidate_contract": exact_contract, "verified": True}
        original_read_json = self.module.read_json
        self.module.repro.LINKED_VALIDATOR_ADAPTERS[source_contract_id] = adapter_name
        sys.modules[adapter_name] = types.SimpleNamespace(
            EXPECTED_SOURCE_CONTRACT_ID="different-contract",
            check=lambda _args: fresh,
        )
        self.module.read_json = lambda *_args: (fresh, b"fresh\n")
        try:
            with self.assertRaisesRegex(
                self.module.CheckError, "adapter contract mismatch"
            ):
                self.module.verify_repro(
                    ROOT, self.module.parse_args([]), exact_contract
                )
        finally:
            self.module.read_json = original_read_json
            self.module.repro.LINKED_VALIDATOR_ADAPTERS.pop(
                source_contract_id, None
            )
            sys.modules.pop(adapter_name, None)

    def test_p280_rootfs_entrypoint_context_wraps_exact_userspace(self):
        source_contract_id = self.module.repro.P280_SOURCE_CONTRACT_ID
        state = {"active": False}

        @contextmanager
        def expected_entrypoints(values):
            self.assertEqual(
                values, {"init": 0x403B20, "child": 0x4000CC}
            )
            state["active"] = True
            try:
                yield
            finally:
                state["active"] = False

        closure = types.SimpleNamespace(
            source_contract=types.SimpleNamespace(
                CONTRACT_ID=source_contract_id
            ),
            _expected_entrypoints=expected_entrypoints,
        )
        with mock.patch.object(
            self.module.e1_static,
            "inspect_static_elf",
            side_effect=[
                {"entrypoint": 0x403B20},
                {"entrypoint": 0x4000CC},
            ],
        ):
            context = self.module.rootfs_entrypoint_context(
                closure,
                {"source_contract_id": source_contract_id},
                {"init": b"init", "child": b"child"},
            )
            with context:
                self.assertTrue(state["active"])
        self.assertFalse(state["active"])

    def test_p280_rootfs_entrypoint_context_rejects_wrong_adapter(self):
        with self.assertRaisesRegex(
            self.module.CheckError, "entrypoint adapter mismatch"
        ):
            self.module.rootfs_entrypoint_context(
                types.SimpleNamespace(),
                {
                    "source_contract_id": (
                        self.module.repro.P280_SOURCE_CONTRACT_ID
                    )
                },
                {"init": b"init", "child": b"child"},
            )

    def test_p282_rootfs_entrypoint_context_uses_inherited_p280_adapter(self):
        state = {"active": False}

        @contextmanager
        def expected_entrypoints(values):
            self.assertEqual(
                values, {"init": 0x40474C, "child": 0x4000CC}
            )
            state["active"] = True
            try:
                yield
            finally:
                state["active"] = False

        p280 = types.SimpleNamespace(
            source_contract=types.SimpleNamespace(
                CONTRACT_ID=self.module.repro.P280_SOURCE_CONTRACT_ID
            ),
            _expected_entrypoints=expected_entrypoints,
        )
        closure = types.SimpleNamespace(
            source_contract=types.SimpleNamespace(
                CONTRACT_ID=self.module.repro.P282_SOURCE_CONTRACT_ID
            ),
            p280=p280,
        )
        with mock.patch.object(
            self.module.e1_static,
            "inspect_static_elf",
            side_effect=[
                {"entrypoint": 0x40474C},
                {"entrypoint": 0x4000CC},
            ],
        ):
            context = self.module.rootfs_entrypoint_context(
                closure,
                {
                    "source_contract_id": (
                        self.module.repro.P282_SOURCE_CONTRACT_ID
                    )
                },
                {"init": b"init", "child": b"child"},
            )
            with context:
                self.assertTrue(state["active"])
        self.assertFalse(state["active"])

    def test_historical_rootfs_entrypoint_context_is_noop(self):
        with mock.patch.object(
            self.module.e1_static,
            "inspect_static_elf",
            side_effect=AssertionError("historical path inspected ELF"),
        ):
            with self.module.rootfs_entrypoint_context(
                types.SimpleNamespace(),
                {"source_contract_id": "historical-contract"},
                {"init": b"init", "child": b"child"},
            ):
                pass


if __name__ == "__main__":
    unittest.main()
