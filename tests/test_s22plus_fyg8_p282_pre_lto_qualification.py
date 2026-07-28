from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p282_pre_lto_qualification as qualification  # noqa: E402


class P282QualificationTests(unittest.TestCase):
    def _exact_contract(self) -> dict:
        return {
            "run_id": "11" * 16,
            "profile": qualification.p282.PROFILE,
            "source_contract_id": qualification.p282.CONTRACT_ID,
            "patch": {"sha256": "22" * 32},
        }

    def _all_evidence(self) -> dict[str, dict]:
        names = {
            key
            for row in (
                ("candidate", "implementation", "module_trace", "qemu_substrate"),
                ("userspace",),
                ("implementation", "classifier_qemu"),
                ("classifier_qemu",),
                ("focused_tests",),
                ("closure", "focused_tests"),
                ("safety",),
                ("p260_qemu", "kprobe_qemu", "lifecycle_qemu"),
                ("linked_audit",),
                ("geometry",),
                ("timing",),
                ("historical_tests",),
            )
            for key in row
        }
        evidence = {name: {"verified": True} for name in names}
        for index, name in enumerate(
            (
                "classifier_qemu",
                "kprobe_qemu",
                "lifecycle_qemu",
                "linked_audit",
                "p260_qemu",
                "userspace",
            ),
            start=1,
        ):
            evidence[name]["result"] = {
                "size": index,
                "sha256": f"{index:064x}",
            }
        return evidence

    def _write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )

    def test_candidate_binding_is_portable_across_repo_copies(self) -> None:
        exact = self._exact_contract()
        intent_relative = Path("workspace/private/candidate-intent.json")
        patch_relative = Path("workspace/private/candidate.patch")
        with tempfile.TemporaryDirectory(
            prefix="p282-binding-a-"
        ) as raw_a, tempfile.TemporaryDirectory(
            prefix="p282-binding-b-"
        ) as raw_b:
            root_a = Path(raw_a)
            root_b = Path(raw_b)
            for root in (root_a, root_b):
                self._write_json(
                    root / intent_relative,
                    {"contract": "portable", "run_id": exact["run_id"]},
                )
                (root / patch_relative).write_bytes(b"portable patch\n")

            with mock.patch.object(
                qualification.candidate_contract.intent,
                "repo_root",
                return_value=root_a,
            ):
                binding_a = qualification._candidate_binding(
                    exact,
                    root_a / intent_relative,
                    root_a / patch_relative,
                )
            with mock.patch.object(
                qualification.candidate_contract.intent,
                "repo_root",
                return_value=root_b,
            ):
                binding_b = qualification._candidate_binding(
                    exact,
                    root_b / intent_relative,
                    root_b / patch_relative,
                )

            self.assertEqual(binding_a, binding_b)
            self.assertEqual(binding_a["intent"]["path"], str(intent_relative))
            self.assertEqual(binding_a["patch"]["path"], str(patch_relative))

            (root_b / patch_relative).write_bytes(b"changed patch\n")
            with mock.patch.object(
                qualification.candidate_contract.intent,
                "repo_root",
                return_value=root_b,
            ):
                changed = qualification._candidate_binding(
                    exact,
                    root_b / intent_relative,
                    root_b / patch_relative,
                )
            self.assertNotEqual(binding_a, changed)

    def test_gate_implementation_is_portable_across_repo_copies(self) -> None:
        relative_sources = {
            "qualification": Path("workspace/public/qualification.py"),
            "runtime": Path("workspace/public/runtime.inc.c"),
        }

        def gate_for(root: Path) -> dict:
            paths = {
                name: root / relative
                for name, relative in relative_sources.items()
            }
            linked = root / "workspace/public/linked.py"
            for name, path in {**paths, "linked": linked}.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"{name}\n".encode("ascii"))
            with mock.patch.object(
                qualification.candidate_contract.intent,
                "repo_root",
                return_value=root,
            ), mock.patch.object(
                qualification,
                "GATE_IMPLEMENTATION_SOURCES",
                paths,
            ), mock.patch.object(
                qualification,
                "_load_linked_audit_module",
                return_value=SimpleNamespace(__file__=str(linked)),
            ):
                return qualification._gate_implementation()

        with tempfile.TemporaryDirectory(
            prefix="p282-gate-a-"
        ) as raw_a, tempfile.TemporaryDirectory(
            prefix="p282-gate-b-"
        ) as raw_b:
            first = gate_for(Path(raw_a))
            second = gate_for(Path(raw_b))

        self.assertEqual(first, second)
        self.assertEqual(
            first["qualification"]["path"],
            str(relative_sources["qualification"]),
        )
        self.assertEqual(
            first["linked_audit"]["path"],
            "workspace/public/linked.py",
        )

    def test_portable_paths_preserve_external_material_identity(self) -> None:
        root = Path("/repo")
        value = {
            "inside": {"path": "/repo/workspace/private/result.json"},
            "outside": {"path": "/usr/bin/python3"},
            "command": ["/repo/workspace/private/result.json"],
        }
        self.assertEqual(
            qualification._portable_repo_paths(root, value),
            {
                "inside": {"path": "workspace/private/result.json"},
                "outside": {"path": "/usr/bin/python3"},
                "command": ["/repo/workspace/private/result.json"],
            },
        )

    def test_exact_gate_inventory_is_19_and_ordered(self) -> None:
        self.assertEqual(len(qualification.GATE_NAMES), 19)
        self.assertEqual(len(set(qualification.GATE_NAMES)), 19)
        rows = qualification._gate_matrix(self._all_evidence())
        self.assertEqual(
            [row["ordinal"] for row in rows], list(range(1, 20))
        )
        self.assertEqual(
            [row["name"] for row in rows],
            list(qualification.GATE_NAMES),
        )
        self.assertTrue(all(row["verified"] for row in rows))

    def test_gate_matrix_rejects_missing_or_unverified_evidence(self) -> None:
        evidence = self._all_evidence()
        del evidence["classifier_qemu"]
        with self.assertRaisesRegex(
            qualification.QualificationError, "gate 3"
        ):
            qualification._gate_matrix(evidence)
        evidence = self._all_evidence()
        evidence["timing"]["verified"] = False
        with self.assertRaisesRegex(
            qualification.QualificationError, "gate 18"
        ):
            qualification._gate_matrix(evidence)

    def test_linked_audit_import_is_deferred_but_production_fails_closed(
        self,
    ) -> None:
        with mock.patch.object(
            qualification.importlib,
            "import_module",
            side_effect=ImportError("not ready"),
        ):
            with self.assertRaisesRegex(
                qualification.QualificationError, "module is unavailable"
            ):
                qualification._load_linked_audit_module()

    def test_linked_audit_module_identity_is_exact(self) -> None:
        wrong = SimpleNamespace(
            EXPECTED_SOURCE_CONTRACT_ID=qualification.p282.CONTRACT_ID,
            ADAPTER_ID="wrong",
        )
        with mock.patch.object(
            qualification.importlib, "import_module", return_value=wrong
        ):
            with self.assertRaisesRegex(
                qualification.QualificationError, "identity drifted"
            ):
                qualification._load_linked_audit_module()

    def test_linked_audit_receipt_binds_current_module_and_test(self) -> None:
        linked_module = SimpleNamespace(
            EXPECTED_SOURCE_CONTRACT_ID=qualification.p282.CONTRACT_ID,
            ADAPTER_ID="s22plus-fyg8-p282-linked-audit-v1",
            __file__=str(
                SCRIPTS / "s22plus_fyg8_p282_linked_audit.py"
            ),
        )
        test_receipt = {
            "command": [
                sys.executable,
                "-m",
                "unittest",
                "-v",
                str(qualification.LINKED_AUDIT_TEST),
            ],
            "test_count": 12,
            "output_sha256": "33" * 32,
            "sources": {
                str(qualification.LINKED_AUDIT_TEST): qualification._material(
                    ROOT / qualification.LINKED_AUDIT_TEST, "linked test"
                )
            },
            "verified": True,
        }
        known_good = {
            "result": {"path": "/result", "size": 1, "sha256": "44" * 32},
            "result_repo_path": "known-good.json",
            "vmlinux": {
                "path": "/vmlinux",
                "size": 2,
                "sha256": "55" * 32,
            },
            "vmlinux_repo_path": "vmlinux",
            "config": {
                "path": "/config",
                "size": 3,
                "sha256": "66" * 32,
            },
            "config_repo_path": "config",
            "linked_adapter": "s22plus-fyg8-p280-linked-audit-v1",
            "verified": True,
        }
        with mock.patch.object(
            qualification,
            "_load_linked_audit_module",
            return_value=linked_module,
        ), mock.patch.object(
            qualification,
            "_run_test_command",
            return_value=test_receipt,
        ), mock.patch.object(
            qualification,
            "_known_good_linked_binding",
            return_value=known_good,
        ):
            value = qualification.create_linked_audit_receipt(ROOT)
        with tempfile.TemporaryDirectory(
            prefix="p282-linked-", dir=ROOT / "workspace/private"
        ) as raw:
            path = Path(raw) / "linked.json"
            self._write_json(path, value)
            with mock.patch.object(
                qualification,
                "_load_linked_audit_module",
                return_value=linked_module,
            ), mock.patch.object(
                qualification,
                "_known_good_linked_binding",
                return_value=known_good,
            ):
                verified = qualification._verify_linked_audit_receipt(path)
            self.assertTrue(verified["verified"])
            self.assertEqual(
                verified["semantics"]["adapter_id"],
                linked_module.ADAPTER_ID,
            )

            changed = copy.deepcopy(value)
            changed["module"]["sha256"] = "44" * 32
            payload = dict(changed)
            payload.pop("payload_sha256")
            changed["payload_sha256"] = hashlib.sha256(
                qualification._canonical(payload)
            ).hexdigest()
            self._write_json(path, changed)
            with mock.patch.object(
                qualification,
                "_load_linked_audit_module",
                return_value=linked_module,
            ), mock.patch.object(
                qualification,
                "_known_good_linked_binding",
                return_value=known_good,
            ), self.assertRaisesRegex(
                qualification.QualificationError, "module changed"
            ):
                qualification._verify_linked_audit_receipt(path)

    def test_test_runner_rejects_duplicate_inventory(self) -> None:
        path = Path("tests/test_s22plus_fyg8_p282_linked_audit.py")
        with self.assertRaisesRegex(
            qualification.QualificationError, "inventory"
        ):
            qualification._run_test_command(
                ROOT, (path, path), "duplicate"
            )

    def test_test_runner_records_exact_count_and_source_materials(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="ok\nRan 7 tests in 0.123s\n\nOK\n",
        )
        path = Path("tests/test_s22plus_fyg8_p282_linked_audit.py")
        with mock.patch.object(
            qualification.subprocess, "run", return_value=completed
        ):
            result = qualification._run_test_command(
                ROOT, (path,), "focused"
            )
        self.assertEqual(result["test_count"], 7)
        self.assertEqual(set(result["sources"]), {str(path)})
        self.assertTrue(result["verified"])

    def test_current_guard_covers_derived_timing_contract(self) -> None:
        self.assertEqual(qualification.MIN_OBSERVATION_TIMEOUT_SEC, 300)
        self.assertEqual(qualification.MIN_GUARD_LIFETIME_SEC, 360)
        result = qualification._timing_gate()
        self.assertEqual(result["actual_guard_lifetime_sec"], 360)
        self.assertTrue(result["verified"])

    def test_timing_gate_accepts_only_complete_asymmetric_contract(self) -> None:
        source = b"MAX_SEC = 360.0\n"
        with mock.patch.object(
            qualification.p280q, "_stable_read", return_value=source
        ):
            result = qualification._timing_gate()
        self.assertEqual(result["p282_added_cycle_budget_sec"], 60)
        self.assertEqual(result["minimum_observation_timeout_sec"], 300)
        self.assertTrue(result["exact_banner_survives_guard_loss"])
        self.assertTrue(
            result["banner_absence_under_guard_loss_is_indeterminate"]
        )

    def test_current_builder_has_exact_p282_safety_dictionary(self) -> None:
        result = qualification._expected_safety(self._exact_contract())
        self.assertEqual(
            result["userspace_parent_role_write_count"],
            2,
        )
        self.assertFalse(result["host_role_authority"])
        self.assertFalse(
            result["direct_power_clock_reset_mmio_authority"]
        )

    def test_historical_ready_manifests_are_not_requalified(self) -> None:
        names = {
            path.name
            for path in qualification.HISTORICAL_PROCESS_V2_TESTS
        }
        self.assertNotIn(
            "test_s22plus_fyg8_p272_process_v2_ready.py",
            names,
        )
        self.assertNotIn(
            "test_s22plus_fyg8_p276_process_v2_ready.py",
            names,
        )
        self.assertNotIn(
            "test_s22plus_fyg8_p280_process_v2_ready.py",
            names,
        )
        self.assertIn("test_device_action_f1_v2.py", names)
        self.assertIn(
            "test_device_action_cdc_acm_observer_v1.py",
            names,
        )

    def test_safety_dictionary_allows_exact_two_role_writes_no_power_or_host(
        self,
    ) -> None:
        contract = self._exact_contract()
        captured: dict = {}

        def exact_safety(value: dict) -> dict:
            captured.update(value)
            return {
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
                    qualification.spec.SAFETY_USERSPACE_WRITE_SCOPE
                ),
                "usb_scope": qualification.spec.SAFETY_USB_SCOPE,
                "module_init_probe_authority": "active-live-unproved",
                **qualification.spec.RUNTIME_AUTHORITY,
            }

        with mock.patch.object(
            qualification.candidate_builder,
            "artifact_safety",
            side_effect=exact_safety,
        ):
            result = qualification._expected_safety(contract)
        self.assertEqual(
            result["userspace_parent_role_write_count"], 2
        )
        self.assertFalse(result["host_role_authority"])
        self.assertFalse(result["direct_power_clock_reset_mmio_authority"])
        self.assertEqual(captured, contract)

    def _classifier_report(self) -> dict:
        source_root = ROOT
        kernel = (
            source_root
            / qualification.CLASSIFIER_SUBSTRATE_REPO_PATHS["kernel"]
        )
        qemu = (
            source_root
            / qualification.CLASSIFIER_SUBSTRATE_REPO_PATHS["qemu"]
        )
        return {
            "schema": qualification.classifier_qemu.SCHEMA,
            "verdict": qualification.classifier_qemu.VERDICT,
            "details_covered": 46,
            "tuple_count": 567,
            "elapsed_sec": 1.5,
            "command": [
                str(qemu),
                "-kernel",
                str(kernel),
                "-initrd",
                "/initramfs",
            ],
            "substrate": {
                "kernel": {
                    "path": str(kernel),
                    "sha256": qualification.classifier_qemu.PINNED_KERNEL_SHA256,
                    "version": qualification.classifier_qemu.KERNEL_VERSION,
                },
                "config": {
                    "path": str(
                        source_root
                        / qualification.CLASSIFIER_SUBSTRATE_REPO_PATHS[
                            "config"
                        ]
                    ),
                    "sha256": qualification.classifier_qemu.PINNED_CONFIG_SHA256,
                    "version": qualification.classifier_qemu.KERNEL_VERSION,
                },
                "qemu": {
                    "path": str(qemu),
                    "sha256": qualification.classifier_qemu.PINNED_QEMU_SHA256,
                    "version": qualification.classifier_qemu.PINNED_QEMU_VERSION,
                },
                "compiler": {
                    "path": "/compiler",
                    "sha256": "55" * 32,
                    "version": "GNU compiler",
                },
            },
            "production_classifier_sha256": "66" * 32,
            "contract_spec_sha256": "77" * 32,
            "generated_contract_sha256": "88" * 32,
            "guest_source_sha256": "99" * 32,
            "init_sha256": "aa" * 32,
            "initramfs_sha256": "bb" * 32,
            "qemu_output_sha256": "cc" * 32,
            "scope": {
                "validated": [
                    "production P2.82 classifier compiled for AArch64",
                    "exact 46-of-46 C-band classifier fixtures executed",
                    "all 567 final tuple combinations classified and encoded",
                    "pinned generic-arm64 kernel, config, and QEMU substrate",
                ],
                "not_validated": [
                    "S22+ vendor-kernel execution",
                    "S22+ runtime trace acquisition and ordering",
                    "physical USB enumeration",
                    "device flashing",
                ],
            },
        }

    def test_classifier_receipt_binds_production_source_and_pins(self) -> None:
        report = self._classifier_report()

        def material(_path: Path, label: str) -> dict:
            mapping = {
                "P2.82 production classifier": "66" * 32,
                "P2.82 classifier contract spec": "77" * 32,
                "P2.82 classifier QEMU kernel": (
                    qualification.classifier_qemu.PINNED_KERNEL_SHA256
                ),
                "P2.82 classifier QEMU config": (
                    qualification.classifier_qemu.PINNED_CONFIG_SHA256
                ),
                "P2.82 classifier QEMU qemu": (
                    qualification.classifier_qemu.PINNED_QEMU_SHA256
                ),
                "P2.82 classifier QEMU initramfs": "bb" * 32,
            }
            return {"path": f"/{label}", "size": 1, "sha256": mapping[label]}

        with mock.patch.object(
            qualification,
            "_load_json",
            return_value=(
                report,
                {"path": "/result", "size": 1, "sha256": "dd" * 32},
            ),
        ), mock.patch.object(
            qualification, "_material", side_effect=material
        ), mock.patch.object(
            qualification,
            "_result_binding",
            return_value={"result": {}, "result_repo_path": "result"},
        ):
            result = qualification._verify_classifier_qemu(Path("/result"))
        self.assertTrue(result["verified"])
        self.assertEqual(result["semantics"]["details_covered"], 46)
        self.assertEqual(
            result["semantics"]["substrate"]["kernel"]["path"],
            str(qualification.CLASSIFIER_SUBSTRATE_REPO_PATHS["kernel"]),
        )

        def tracked_only_material(_path: Path, label: str) -> dict:
            mapping = {
                "P2.82 production classifier": "66" * 32,
                "P2.82 classifier contract spec": "77" * 32,
            }
            return {
                "path": f"/{label}",
                "size": 1,
                "sha256": mapping[label],
            }

        with mock.patch.object(
            qualification,
            "_load_json",
            return_value=(
                self._classifier_report(),
                {"path": "/result", "size": 1, "sha256": "dd" * 32},
            ),
        ), mock.patch.object(
            qualification,
            "_material",
            side_effect=tracked_only_material,
        ), mock.patch.object(
            qualification,
            "_result_binding",
            return_value={"result": {}, "result_repo_path": "result"},
        ):
            rehydrated = qualification._verify_classifier_qemu(
                Path("/result"), verify_materials=False
            )
        self.assertTrue(rehydrated["verified"])

        report["production_classifier_sha256"] = "ee" * 32
        with mock.patch.object(
            qualification,
            "_load_json",
            return_value=(
                report,
                {"path": "/result", "size": 1, "sha256": "dd" * 32},
            ),
        ), mock.patch.object(
            qualification, "_material", side_effect=material
        ), self.assertRaisesRegex(
            qualification.QualificationError, "source binding changed"
        ):
            qualification._verify_classifier_qemu(Path("/result"))

        report = self._classifier_report()
        report["substrate"]["kernel"]["path"] = "/wrong/kernel"
        with mock.patch.object(
            qualification,
            "_load_json",
            return_value=(
                report,
                {"path": "/result", "size": 1, "sha256": "dd" * 32},
            ),
        ), mock.patch.object(
            qualification, "_material", side_effect=material
        ), self.assertRaisesRegex(
            qualification.QualificationError, "path drifted"
        ):
            qualification._verify_classifier_qemu(Path("/result"))

        report = self._classifier_report()
        report["substrate"]["kernel"]["path"] = str(
            Path("/wrong")
            / qualification.CLASSIFIER_SUBSTRATE_REPO_PATHS["kernel"]
        )
        with mock.patch.object(
            qualification,
            "_load_json",
            return_value=(
                report,
                {"path": "/result", "size": 1, "sha256": "dd" * 32},
            ),
        ), mock.patch.object(
            qualification, "_material", side_effect=material
        ), self.assertRaisesRegex(
            qualification.QualificationError, "path drifted"
        ):
            qualification._verify_classifier_qemu(Path("/result"))

        for field in ("qemu", "kernel"):
            report = self._classifier_report()
            command_index = (
                0
                if field == "qemu"
                else report["command"].index("-kernel") + 1
            )
            report["command"][command_index] = "/wrong"
            with mock.patch.object(
                qualification,
                "_load_json",
                return_value=(
                    report,
                    {"path": "/result", "size": 1, "sha256": "dd" * 32},
                ),
            ), mock.patch.object(
                qualification, "_material", side_effect=material
            ), self.assertRaisesRegex(
                qualification.QualificationError,
                "command substrate drifted",
            ):
                qualification._verify_classifier_qemu(Path("/result"))

    def test_userspace_gate_uses_derived_entrypoints_and_authority(self) -> None:
        contract = self._exact_contract()
        with tempfile.TemporaryDirectory(
            prefix="p282-userspace-", dir=ROOT / "workspace/private"
        ) as raw:
            directory = Path(raw)
            init = b"fake-init"
            child = b"fake-child"
            (directory / "init").write_bytes(init)
            (directory / "s22-e1-child").write_bytes(child)
            value = {
                "schema": qualification.userspace.SCHEMA,
                "verdict": qualification.p282.USERSPACE_VERDICT,
                "candidate_contract": contract,
                "compile_flags": [],
                "outputs": {
                    "init": qualification._receipt_bytes(init),
                    "child": qualification._receipt_bytes(child),
                },
                "profile": qualification.p282.PROFILE,
                "run_id": contract["run_id"],
                "safety": {},
                "source_contract": {"verified": True},
                "target": "S22+",
                "two_build_byte_identical": True,
            }
            result_path = directory / "userspace-result.json"
            self._write_json(result_path, value)
            with mock.patch.object(
                qualification.closure,
                "_entrypoints",
                return_value={"init": 0x401000, "child": 0x402000},
            ), mock.patch.object(
                qualification.closure, "_validate_p282_authority_strings"
            ) as authority:
                result = qualification._verify_userspace(
                    result_path, contract
                )
            authority.assert_called_once_with(init)
            self.assertEqual(
                result["semantics"]["entrypoints"]["init"], 0x401000
            )
            self.assertTrue(
                result["semantics"]["same_path_two_link_byte_identical"]
            )

            value["outputs"]["init"]["sha256"] = "ff" * 32
            self._write_json(result_path, value)
            with mock.patch.object(
                qualification.closure,
                "_entrypoints",
                return_value={"init": 0x401000, "child": 0x402000},
            ), self.assertRaisesRegex(
                qualification.QualificationError, "receipt mismatch"
            ):
                qualification._verify_userspace(result_path, contract)

    def _qualification_value(
        self,
        exact_contract: dict,
        candidate: dict,
        implementation: dict,
        gate_implementation: dict,
        evidence: dict,
    ) -> dict:
        payload = {
            "schema": qualification.SCHEMA,
            "verdict": qualification.VERDICT,
            "build_allowed": True,
            "candidate": candidate,
            "implementation": implementation,
            "gate_implementation": gate_implementation,
            "evidence": evidence,
            "gates": qualification._gate_matrix(evidence),
            "safety": {
                "host_only": True,
                "kernel_built": False,
                "full_lto_started": False,
                "candidate_created": False,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "live_authorized": False,
            },
        }
        return {
            **payload,
            "payload_sha256": hashlib.sha256(
                qualification._canonical(payload)
            ).hexdigest(),
        }

    def test_verify_receipt_rejects_stale_input_and_source_binding(self) -> None:
        exact = self._exact_contract()
        candidate = {
            "run_id": exact["run_id"],
            "intent_repo_path": "intent",
            "patch_repo_path": "patch",
        }
        implementation = {
            "schema": "implementation",
            "verdict": qualification.p282.IMPLEMENTATION_VERDICT,
            "generated": {"x": {"size": 1, "sha256": "11" * 32}},
            "source_receipts": {"x": {"size": 1, "sha256": "22" * 32}},
            "verified": True,
        }
        gate_implementation = {"verified": True}
        evidence = self._all_evidence()
        evidence["safety"] = {
            "dictionary": {"authority": "exact"},
            "verified": True,
        }
        evidence["timing"] = {"budget": 360, "verified": True}
        evidence["linked_audit"] = {
            "result_repo_path": "workspace/private/linked.json",
            "result": {
                "size": 4,
                "sha256": f"{4:064x}",
            },
            "verified": True,
        }
        value = self._qualification_value(
            exact,
            candidate,
            implementation,
            gate_implementation,
            evidence,
        )
        with tempfile.TemporaryDirectory(
            prefix="p282-qualification-", dir=ROOT / "workspace/private"
        ) as raw:
            path = Path(raw) / "qualification.json"
            self._write_json(path, value)
            patches = (
                mock.patch.object(
                    qualification,
                    "_candidate_binding",
                    return_value=candidate,
                ),
                mock.patch.object(
                    qualification.p282,
                    "implementation_result",
                    return_value={
                        "schema": "implementation",
                        "verdict": qualification.p282.IMPLEMENTATION_VERDICT,
                        "generated": implementation["generated"],
                    },
                ),
                mock.patch.object(
                    qualification.p282,
                    "source_receipts",
                    return_value=({}, implementation["source_receipts"]),
                ),
                mock.patch.object(
                    qualification,
                    "_gate_implementation",
                    return_value=gate_implementation,
                ),
                mock.patch.object(
                    qualification,
                    "_current_evidence",
                    return_value=evidence,
                ),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                result = qualification.verify_receipt(
                    path,
                    exact,
                    intent_path=ROOT / "intent",
                    patch_path=ROOT / "patch",
                )
                integrated = repro.verify_p282_qualification_file(
                    result,
                    exact,
                    intent_path=ROOT / "intent",
                    patch_path=ROOT / "patch",
                    root=ROOT,
                )
            self.assertTrue(result["verified"])
            self.assertEqual(result["gate_count"], 19)
            self.assertEqual(
                result["gate_result_receipts"],
                qualification._gate_result_receipts(evidence),
            )
            self.assertEqual(integrated, result)

            stale = copy.deepcopy(value)
            stale["candidate"]["run_id"] = "33" * 16
            payload = dict(stale)
            payload.pop("payload_sha256")
            stale["payload_sha256"] = hashlib.sha256(
                qualification._canonical(payload)
            ).hexdigest()
            self._write_json(path, stale)
            with patches[0], patches[1], patches[2], patches[3], patches[4], self.assertRaisesRegex(
                qualification.QualificationError, "different inputs"
            ):
                qualification.verify_receipt(
                    path,
                    exact,
                    intent_path=ROOT / "intent",
                    patch_path=ROOT / "patch",
                )

            stale = copy.deepcopy(value)
            stale["implementation"]["source_receipts"]["x"]["sha256"] = (
                "44" * 32
            )
            payload = dict(stale)
            payload.pop("payload_sha256")
            stale["payload_sha256"] = hashlib.sha256(
                qualification._canonical(payload)
            ).hexdigest()
            self._write_json(path, stale)
            with patches[0], patches[1], patches[2], patches[3], patches[4], self.assertRaisesRegex(
                qualification.QualificationError, "source binding is stale"
            ):
                qualification.verify_receipt(
                    path,
                    exact,
                    intent_path=ROOT / "intent",
                    patch_path=ROOT / "patch",
                )

    def test_qualification_top_level_extra_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="p282-shape-", dir=ROOT / "workspace/private"
        ) as raw:
            path = Path(raw) / "qualification.json"
            self._write_json(path, {"extra": True})
            with self.assertRaisesRegex(
                qualification.QualificationError, "schema is not exact"
            ):
                qualification.verify_receipt(
                    path,
                    self._exact_contract(),
                    intent_path=ROOT / "intent",
                    patch_path=ROOT / "patch",
                )


if __name__ == "__main__":
    unittest.main()
