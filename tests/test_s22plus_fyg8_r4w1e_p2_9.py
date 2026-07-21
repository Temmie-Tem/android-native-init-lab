import ast
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"


def load(name, file_name):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file_name)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1EP29Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_adapter = load(
            "s22plus_fyg8_r4w1e_build_tested", "s22plus_fyg8_r4w1e_build.py"
        )
        cls.builder = load(
            "build_s22plus_fyg8_r4w1e_e1_candidate_tested",
            "build_s22plus_fyg8_r4w1e_e1_candidate.py",
        )
        cls.checker = load(
            "s22plus_fyg8_r4w1e_e1_candidate_static_checker_tested",
            "s22plus_fyg8_r4w1e_e1_candidate_static_checker.py",
        )

    def test_build_adapter_binds_exact_e_contract_and_restores_engine(self):
        engine = self.build_adapter.engine
        names = (
            "SCHEMA",
            "EXECUTION_SCRIPT",
            "contract",
            "PROOF_BYTES",
            "PROOF_FAMILY",
            "HISTORICAL_FAMILIES",
            "HISTORICAL_CONFIGS",
            "CONTRACT_RESULT_KEY",
            "BUILD_PASS_KEY",
            "parse_args",
        )
        before = {name: getattr(engine, name) for name in names}
        with self.build_adapter.bind_engine():
            self.assertEqual(engine.SCHEMA, self.build_adapter.SCHEMA)
            self.assertEqual(engine.PROOF_BYTES, self.build_adapter.checkpoint.ENTRY_PROOF)
            self.assertEqual(engine.contract.CONFIG, self.build_adapter.checkpoint.CONFIG)
            self.assertEqual(engine.contract.VERDICT, self.build_adapter.checkpoint.VERDICT)
            self.assertEqual(
                engine.contract.PATCH_SHA256,
                self.build_adapter.checkpoint.PATCH_SHA256,
            )
            self.assertEqual(
                engine.contract.BASE_FILES,
                self.build_adapter.checkpoint.BASE_FILES,
            )
            self.assertEqual(
                engine.contract.PATCHED_FILES,
                self.build_adapter.checkpoint.PATCHED_FILES,
            )
            self.assertEqual(engine.CONTRACT_RESULT_KEY, "r4w1e_checkpoint_contract")
            self.assertEqual(engine.BUILD_PASS_KEY, "r4w1e_build_pass")
            self.assertIn(b"[[S22P1D|", engine.HISTORICAL_FAMILIES)
            self.assertIn(
                "CONFIG_S22PLUS_FYG8_COMPACT_RETAINED_WITNESS",
                engine.HISTORICAL_CONFIGS,
            )
        for name, value in before.items():
            self.assertIs(getattr(engine, name), value)

    def test_build_adapter_restores_after_error(self):
        engine = self.build_adapter.engine
        previous = engine.contract
        with self.assertRaisesRegex(RuntimeError, "stop"):
            with self.build_adapter.bind_engine():
                raise RuntimeError("stop")
        self.assertIs(engine.contract, previous)

    def binding_inputs(self):
        digest = lambda value: {
            "size": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
        }
        sources = {
            name: {"size": index + 1, "sha256": value}
            for index, (name, value) in enumerate(
                self.builder.e1.EXPECTED_SOURCE_SHA256.items()
            )
        }
        tools = {
            name: {
                "resolved_name": name,
                "size": 1,
                "sha256": hashlib.sha256(name.encode()).hexdigest(),
            }
            for name in (
                "aarch64-linux-gnu-gcc",
                "aarch64-linux-gnu-strip",
                "aarch64-linux-gnu-readelf",
                "aarch64-linux-gnu-nm",
                "aarch64-linux-gnu-objdump",
                "gcc",
                "file",
                "qemu-aarch64",
            )
        }
        return {
            "image": digest(b"image"),
            "kernel_result": digest(b"result"),
            "base_boot": {
                "size": self.builder.BOOT_SIZE,
                "sha256": self.builder.carrier_engine.EXPECTED_BASE_BOOT_SHA256,
            },
            "vendor_ramdisk": {
                "size": self.builder.carrier_engine.VENDOR_RAMDISK_SIZE,
                "sha256": self.builder.carrier_engine.VENDOR_RAMDISK_SHA256,
            },
            "lz4": {
                "size": self.builder.slice_engine.LZ4_SIZE,
                "sha256": self.builder.slice_engine.LZ4_SHA256,
            },
            "magiskboot": {
                "size": self.builder.carrier_engine.MAGISKBOOT_SIZE,
                "sha256": self.builder.carrier_engine.MAGISKBOOT_SHA256,
            },
            "sources": sources,
            "tools": tools,
        }

    def derive(self, nonce=b"\x11" * 16):
        return self.builder.derive_run_manifest(nonce=nonce, **self.binding_inputs())

    def checker_binding(self):
        inputs = self.binding_inputs()
        return {
            "fixed_receipts": {
                name: inputs[name]
                for name in ("base_boot", "vendor_ramdisk", "lz4", "magiskboot")
            },
            "source_receipts": inputs["sources"],
            "actual_tool_receipts": inputs["tools"],
        }

    def test_run_manifest_is_deterministic_fresh_and_checker_exact(self):
        manifest_a, encoded_a, run_a = self.derive()
        manifest_b, encoded_b, run_b = self.derive()
        self.assertEqual((manifest_a, encoded_a, run_a), (manifest_b, encoded_b, run_b))
        self.assertNotEqual(run_a, bytes(16))
        self.assertNotEqual(run_a, self.builder.checkpoint.MODEL_RUN_IDS["E1"])
        decoded, checked_encoded, checked_run = self.checker.verify_run_manifest(
            json.dumps(manifest_a).encode("ascii"),
            image_receipt=self.binding_inputs()["image"],
            kernel_result_receipt=self.binding_inputs()["kernel_result"],
            **self.checker_binding(),
        )
        self.assertEqual(decoded, manifest_a)
        self.assertEqual(checked_encoded, encoded_a)
        self.assertEqual(checked_run, run_a)

    def test_run_manifest_nonce_and_input_mutation_change_identity(self):
        _, _, first = self.derive(b"\x21" * 16)
        _, _, second = self.derive(b"\x22" * 16)
        self.assertNotEqual(first, second)
        inputs = self.binding_inputs()
        inputs["image"] = {**inputs["image"], "sha256": "0" * 64}
        _, _, third = self.builder.derive_run_manifest(nonce=b"\x21" * 16, **inputs)
        self.assertNotEqual(first, third)

    def test_checker_rejects_run_manifest_source_and_tool_substitution(self):
        manifest, _, _ = self.derive()
        for mutate in ("source", "tool", "compile_flags", "child_exit"):
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(manifest)
                if mutate == "source":
                    changed["inputs"]["sources"]["runtime"]["sha256"] = "0" * 64
                elif mutate == "tool":
                    del changed["inputs"]["host_tools"]["file"]
                elif mutate == "compile_flags":
                    changed["inputs"]["runtime_contract"]["compile_flags"].append(
                        "-funsafe-math-optimizations"
                    )
                else:
                    changed["inputs"]["runtime_contract"]["child_exit"] += 1
                with self.assertRaises(self.checker.CheckError):
                    self.checker.verify_run_manifest(
                        json.dumps(changed).encode("ascii"),
                        image_receipt=self.binding_inputs()["image"],
                        kernel_result_receipt=self.binding_inputs()["kernel_result"],
                        **self.checker_binding(),
                    )

    def test_checker_rejects_manifest_receipts_not_matching_actual_inputs(self):
        manifest, _, _ = self.derive()
        for name in ("source_receipts", "actual_tool_receipts"):
            with self.subTest(name=name):
                actual = copy.deepcopy(self.checker_binding())
                key = "runtime" if name == "source_receipts" else "gcc"
                actual[name][key]["sha256"] = "0" * 64
                with self.assertRaises(self.checker.CheckError):
                    self.checker.verify_run_manifest(
                        json.dumps(manifest).encode("ascii"),
                        image_receipt=self.binding_inputs()["image"],
                        kernel_result_receipt=self.binding_inputs()["kernel_result"],
                        **actual,
                    )

    def test_json_contracts_reject_non_object_top_levels(self):
        with self.assertRaises(self.builder.BuildError):
            self.builder.verify_kernel_build(b"[]", b"image")
        with self.assertRaises(self.checker.CheckError):
            self.checker.verify_kernel_result(b"[]", self.builder.receipt(b"image"))
        with self.assertRaises(self.checker.CheckError):
            self.checker.verify_run_manifest(
                b"[]",
                image_receipt=self.binding_inputs()["image"],
                kernel_result_receipt=self.binding_inputs()["kernel_result"],
                **self.checker_binding(),
            )

    def fake_kernel_result(self, image):
        image_receipt = self.builder.receipt(image)
        return {
            "schema": "s22plus_fyg8_r4w1e_build_v1",
            "target": self.builder.TARGET,
            "mode": "build",
            "returncode": 0,
            "r4w1e_build_pass": True,
            "source_delta": {
                "verified": True,
                "restored": True,
                "patch_sha256": self.builder.checkpoint.PATCH_SHA256,
            },
            "source_symlink_control_runtime": {
                "verified": True,
                "runtime_override_count": 1,
                "qualified_external_symlink_count": 1,
                "links": [
                    {
                        "relative_path": self.builder.SOURCE_CLANG_LINK,
                        "provenance": "separately-pinned-toolchain-link",
                        "runtime_override_applied": True,
                        "runtime_target": "/qualified/clang-r416183b",
                        "post_build_target": "/qualified/clang-r416183b",
                        "target_mutated_by_build": False,
                        "restored": True,
                        "path_identity_verified": True,
                    }
                ],
            },
            "output_gate": {"verified": True},
            "module_gate": {"verified": True},
            "kernel_banner_gate": {"verified": True},
            "witness_output_gate": {
                "verified": True,
                "image_size": self.builder.KERNEL_SIZE,
                "image_proof_count": 1,
                "vmlinux_proof_count": 1,
                "image_proof_family_count": 1,
                "vmlinux_proof_family_count": 1,
                "config_enable_count": 1,
                "fips_enable_count": 1,
                "historical_config_enable_counts": {
                    "CONFIG_S22PLUS_FYG8_COMPACT_RETAINED_WITNESS": 0
                },
            },
            "sec_log_buf_timing_gate": {"verified": True},
            "exclusive_output_root": {"verified": True},
            "r4w1e_checkpoint_contract": {"verdict": self.builder.checkpoint.VERDICT},
            "outputs": [{"name": "Image", **image_receipt}],
            "safety": {
                "host_only": True,
                "device_contact": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "packaging_outputs_promoted": False,
            },
        }

    def pin_build_artifacts(self, image, encoded_result):
        self.assertIs(self.builder.build_artifact, self.checker.build_artifact)
        return mock.patch.multiple(
            self.builder.build_artifact,
            IMAGE_SIZE=len(image),
            IMAGE_SHA256=hashlib.sha256(image).hexdigest(),
            KERNEL_BUILD_RESULT_SIZE=len(encoded_result),
            KERNEL_BUILD_RESULT_SHA256=hashlib.sha256(encoded_result).hexdigest(),
        )

    def test_kernel_build_result_is_bound_and_fail_closed(self):
        image = b"kernel"
        result = self.fake_kernel_result(image)
        encoded = json.dumps(result).encode()
        with self.pin_build_artifacts(image, encoded):
            checked = self.builder.verify_kernel_build(encoded, image)
            self.assertTrue(checked["verified"])
            independent = self.checker.verify_kernel_result(
                encoded, self.builder.receipt(image)
            )
            self.assertTrue(independent["verified"])
        for path, value in (
            (("source_delta", "restored"), False),
            (("witness_output_gate", "image_proof_count"), 2),
            (("source_symlink_control_runtime", "runtime_override_count"), 0),
            (("safety", "live_authorized"), True),
        ):
            with self.subTest(path=path):
                changed = copy.deepcopy(result)
                changed[path[0]][path[1]] = value
                changed_encoded = json.dumps(changed).encode()
                with self.pin_build_artifacts(image, changed_encoded):
                    with self.assertRaises(
                        (self.builder.BuildError, self.checker.CheckError)
                    ):
                        self.builder.verify_kernel_build(changed_encoded, image)
                    with self.assertRaises(
                        (self.builder.BuildError, self.checker.CheckError)
                    ):
                        self.checker.verify_kernel_result(
                            changed_encoded, self.builder.receipt(image)
                        )

    def test_immutable_build_artifact_contract_rejects_mutation(self):
        image = b"kernel"
        encoded = json.dumps(self.fake_kernel_result(image)).encode()
        with self.pin_build_artifacts(image, encoded):
            for changed_image, changed_result in (
                (image + b"X", encoded),
                (image, encoded + b" "),
            ):
                with self.subTest(
                    image_changed=changed_image != image,
                    result_changed=changed_result != encoded,
                ):
                    with self.assertRaises(self.builder.BuildError):
                        self.builder.verify_kernel_build(changed_result, changed_image)
                    with self.assertRaises(self.checker.CheckError):
                        self.checker.verify_kernel_result(
                            changed_result, self.builder.receipt(changed_image)
                        )

    def test_nonce_parser_is_exact(self):
        self.assertEqual(self.builder.parse_nonce("ab" * 16), bytes.fromhex("ab" * 16))
        for value in ("", "0" * 31, "g" * 32):
            with self.subTest(value=value):
                with self.assertRaises(self.builder.BuildError):
                    self.builder.parse_nonce(value)

    def test_scripts_have_no_device_or_odin_execution_path(self):
        for name in (
            "build_s22plus_fyg8_r4w1e_e1_candidate.py",
            "s22plus_fyg8_r4w1e_e1_candidate_static_checker.py",
        ):
            text = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertNotIn("run_odin", text)
            self.assertNotIn('"adb"', text.lower())
            self.assertNotIn("fastboot", text.lower())
            self.assertIn('"device_contact": False', text)
            self.assertIn('"live_authorized": False', text)

    def test_static_elf_rejects_non_elf(self):
        with self.assertRaises(self.checker.CheckError):
            self.checker.inspect_static_elf(b"not-elf", "fixture")

    def test_imported_e1_attribute_references_exist(self):
        for name in (
            "build_s22plus_fyg8_r4w1e_e1_candidate.py",
            "s22plus_fyg8_r4w1e_e1_candidate_static_checker.py",
        ):
            with self.subTest(name=name):
                tree = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))
                references = {
                    node.attr
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "e1"
                }
                missing = sorted(
                    attribute
                    for attribute in references
                    if not hasattr(self.builder.e1, attribute)
                )
                self.assertEqual(missing, [])

    def test_checker_rejects_submitted_carrier_not_exactly_reconstructed(self):
        carrier = b"exact-carrier"
        self.checker.require_reconstructed_carrier(carrier, carrier)
        with self.assertRaises(self.checker.CheckError):
            self.checker.require_reconstructed_carrier(
                carrier[:-1] + b"X", carrier
            )

    def test_checker_accepts_only_one_exact_boot_ap_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            frame = b"deterministic-frame"
            ap = Path(temporary) / "AP.tar.md5"
            self.builder.boot_slice.write_deterministic_boot_ap(frame, ap)
            result = self.checker.verify_exact_boot_ap(ap.read_bytes(), frame)
            self.assertEqual(result["member"]["name"], "boot.img.lz4")
            with self.assertRaises(self.checker.CheckError):
                self.checker.verify_exact_boot_ap(ap.read_bytes(), frame + b"X")

    def test_audit_binds_pinned_inputs_to_independent_reconstruction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate"
            (candidate / "odin4").mkdir(parents=True)
            paths = {
                "carrier": candidate / "carrier.boot.img",
                "candidate": candidate / "boot.img",
                "frame": candidate / "boot.img.lz4",
                "ap": candidate / "odin4/AP.tar.md5",
                "manifest": candidate / "manifest.json",
                "run_manifest": candidate / "run-manifest.json",
            }
            image_path = root / "Image"
            kernel_result_path = root / "kernel-result.json"
            fixed_paths = {
                "base": root / "base.boot.img",
                "vendor_ramdisk": root / "vendor_ramdisk00",
                "lz4": root / "lz4",
                "magiskboot": root / "magiskboot",
            }
            vendor_boot_path = root / "vendor_boot.img"
            for path in (
                *paths.values(),
                image_path,
                kernel_result_path,
                *fixed_paths.values(),
                vendor_boot_path,
            ):
                path.touch()
            submitted_carrier = b"submitted-carrier"
            image = self.checker.checkpoint.ENTRY_PROOF
            artifact_values = {
                paths["carrier"]: (
                    {"size": self.checker.BOOT_SIZE, "sha256": "1" * 64},
                    submitted_carrier,
                ),
                paths["candidate"]: (
                    {"size": self.checker.BOOT_SIZE, "sha256": "2" * 64},
                    b"candidate",
                ),
                paths["frame"]: ({"size": 1, "sha256": "3" * 64}, b"frame"),
                paths["ap"]: ({"size": 1, "sha256": "4" * 64}, b"ap"),
                paths["manifest"]: (
                    {"size": 2, "sha256": "5" * 64},
                    b"{}",
                ),
                paths["run_manifest"]: (
                    {"size": 2, "sha256": "6" * 64},
                    b"{}",
                ),
                image_path: (
                    {"size": self.checker.KERNEL_SIZE, "sha256": "7" * 64},
                    image,
                ),
                kernel_result_path: (
                    {"size": 2, "sha256": "8" * 64},
                    b"{}",
                ),
            }
            fixed_values = {
                fixed_paths["base"]: (
                    {
                        "size": self.checker.BOOT_SIZE,
                        "sha256": self.checker.carrier_inputs.EXPECTED_BASE_BOOT_SHA256,
                    },
                    b"pinned-base",
                ),
                fixed_paths["vendor_ramdisk"]: (
                    {
                        "size": self.checker.carrier_inputs.VENDOR_RAMDISK_SIZE,
                        "sha256": self.checker.carrier_inputs.VENDOR_RAMDISK_SHA256,
                    },
                    b"pinned-vendor-ramdisk",
                ),
                fixed_paths["lz4"]: (
                    {
                        "size": self.checker.base_static.LZ4_SIZE,
                        "sha256": self.checker.base_static.LZ4_SHA256,
                    },
                    b"pinned-lz4",
                ),
                fixed_paths["magiskboot"]: (
                    {
                        "size": self.checker.carrier_inputs.MAGISKBOOT_SIZE,
                        "sha256": self.checker.carrier_inputs.MAGISKBOOT_SHA256,
                    },
                    b"pinned-magiskboot",
                ),
            }
            source_data = {
                name: name.encode()
                for name in self.checker.e1.EXPECTED_SOURCE_SHA256
            }
            source_receipts = {
                name: {"size": len(data), "sha256": digest}
                for (name, digest), data in zip(
                    self.checker.e1.EXPECTED_SOURCE_SHA256.items(),
                    source_data.values(),
                    strict=True,
                )
            }
            tools = {"gcc": "/usr/bin/gcc"}
            tool_rows = {
                "gcc": {"resolved_name": "gcc", "size": 1, "sha256": "9" * 64}
            }
            run_id = b"\x31" * 16
            args = SimpleNamespace(
                candidate=candidate,
                image=image_path,
                kernel_result=kernel_result_path,
                base_boot=fixed_paths["base"],
                vendor_ramdisk=fixed_paths["vendor_ramdisk"],
                vendor_boot=vendor_boot_path,
                lz4=fixed_paths["lz4"],
                magiskboot=fixed_paths["magiskboot"],
            )
            with (
                mock.patch.object(
                    self.checker,
                    "repo_root",
                    return_value=root,
                ),
                mock.patch.object(
                    self.checker,
                    "file_receipt",
                    side_effect=lambda path, _label: artifact_values[path],
                ),
                mock.patch.object(
                    self.checker.verify,
                    "parse_arm64_header",
                    return_value={},
                ),
                mock.patch.object(
                    self.checker,
                    "verify_kernel_result",
                    return_value={"verified": True},
                ),
                mock.patch.object(
                    self.checker.verify,
                    "read_pinned_stable",
                    side_effect=lambda path, *_args: fixed_values[path],
                ),
                mock.patch.object(
                    self.checker,
                    "exact_source_data",
                    return_value=(source_data, source_receipts),
                ),
                mock.patch.object(
                    self.checker.e1,
                    "run_check",
                    return_value={"verdict": self.checker.e1.VERDICT},
                ),
                mock.patch.object(
                    self.checker.e1,
                    "require_tools",
                    return_value=tools,
                ),
                mock.patch.object(
                    self.checker,
                    "tool_receipts",
                    return_value=tool_rows,
                ),
                mock.patch.object(
                    self.checker,
                    "verify_run_manifest",
                    return_value=({}, b"run", run_id),
                ) as verify_manifest,
                mock.patch.object(
                    self.checker,
                    "reconstruct_carrier",
                    return_value=(b"independent-carrier", {"compiled": {}}),
                ) as reconstruct,
            ):
                with self.assertRaisesRegex(
                    self.checker.CheckError,
                    "differs from independent reconstruction",
                ):
                    self.checker.audit(args)
            reconstruct.assert_called_once_with(
                base_boot=b"pinned-base",
                magiskboot=b"pinned-magiskboot",
                source_data=source_data,
                run_id=run_id,
                tools=tools,
            )
            manifest_call = verify_manifest.call_args.kwargs
            self.assertEqual(manifest_call["source_receipts"], source_receipts)
            self.assertEqual(manifest_call["actual_tool_receipts"], tool_rows)
            self.assertEqual(
                manifest_call["fixed_receipts"]["base_boot"],
                fixed_values[fixed_paths["base"]][0],
            )


if __name__ == "__main__":
    unittest.main()
