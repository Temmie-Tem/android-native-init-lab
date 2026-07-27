#!/usr/bin/env python3
"""Focused tests for the P2.80 pre-Full-LTO qualification gate."""

from __future__ import annotations

import argparse
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p234_build as build  # noqa: E402
import s22plus_fyg8_p260_source_contract as p260  # noqa: E402
import s22plus_fyg8_p280_pre_lto_qualification as qualification  # noqa: E402


class P280PreLtoQualificationTests(unittest.TestCase):
    def setUp(self):
        self.contract = {
            "schema": qualification.p280.CONTRACT_SCHEMA,
            "verdict": qualification.p280.CONTRACT_VERDICT,
            "verified": True,
            "profile": "E2",
            "source_contract_id": qualification.p280.CONTRACT_ID,
            "run_id": "11" * 16,
            "patch": {"size": 7, "sha256": "22" * 32},
            "base_files": {},
            "patched_files": {},
        }
        build._bound_pre_lto_qualification = None

    def _args(self, qualification_path: Path | None) -> argparse.Namespace:
        return argparse.Namespace(
            work_tree=Path("source"),
            intent=Path("intent.json"),
            patch=Path("candidate.patch"),
            pre_lto_qualification=qualification_path,
        )

    def test_p280_build_refuses_missing_qualification(self):
        with mock.patch.object(
            build.candidate_contract, "verify", return_value=self.contract
        ):
            with self.assertRaisesRegex(
                build.BuildError, "requires --pre-lto-qualification"
            ):
                build._configure_contract(self._args(None))

    def test_p280_build_binds_exact_qualification(self):
        summary = {
            "schema": qualification.SCHEMA,
            "verdict": qualification.VERDICT,
            "build_allowed": True,
            "verified": True,
        }
        with mock.patch.object(
            build.candidate_contract, "verify", return_value=self.contract
        ), mock.patch.object(
            build.p280_qualification,
            "verify_receipt",
            return_value=summary,
        ) as verify:
            result = build._configure_contract(
                self._args(Path("workspace/private/qualification.json"))
            )
        self.assertIs(result, self.contract)
        self.assertEqual(build._bound_pre_lto_qualification, summary)
        verify.assert_called_once_with(
            ROOT / "workspace/private/qualification.json",
            self.contract,
            intent_path=ROOT / "intent.json",
            patch_path=ROOT / "candidate.patch",
        )

    def test_p280_build_rejects_stale_qualification(self):
        with mock.patch.object(
            build.candidate_contract, "verify", return_value=self.contract
        ), mock.patch.object(
            build.p280_qualification,
            "verify_receipt",
            side_effect=qualification.QualificationError("stale run ID"),
        ):
            with self.assertRaisesRegex(build.BuildError, "stale run ID"):
                build._configure_contract(
                    self._args(Path("workspace/private/qualification.json"))
                )

    def test_historical_contract_does_not_require_qualification(self):
        historical = {
            **self.contract,
            "schema": p260.CONTRACT_SCHEMA,
            "verdict": p260.CONTRACT_VERDICT,
            "source_contract_id": p260.CONTRACT_ID,
        }
        with mock.patch.object(
            build.candidate_contract, "verify", return_value=historical
        ), mock.patch.object(
            build.p280_qualification, "verify_receipt"
        ) as verify:
            result = build._configure_contract(self._args(None))
        self.assertIs(result, historical)
        self.assertIsNone(build._bound_pre_lto_qualification)
        verify.assert_not_called()

    def test_qualified_preflight_records_receipt_and_controls_build(self):
        summary = {
            "schema": qualification.SCHEMA,
            "verdict": qualification.VERDICT,
            "build_allowed": True,
            "verified": True,
        }
        build._ContractAdapter._bound_result = self.contract
        build._bound_pre_lto_qualification = summary
        previous = build._active_base_preflight
        try:
            build._active_base_preflight = lambda *_args, **_kwargs: {
                "build_allowed": True,
                "provenance": {},
            }
            result = build.qualified_preflight()
        finally:
            build._active_base_preflight = previous
        self.assertTrue(result["build_allowed"])
        self.assertEqual(
            result["provenance"]["p280_pre_lto_qualification"], summary
        )

    def test_qualified_preflight_refuses_unbound_receipt(self):
        build._ContractAdapter._bound_result = self.contract
        build._bound_pre_lto_qualification = None
        previous = build._active_base_preflight
        try:
            build._active_base_preflight = lambda *_args, **_kwargs: {
                "build_allowed": True,
                "provenance": {},
            }
            with self.assertRaisesRegex(
                build.BuildError, "qualification is not bound"
            ):
                build.qualified_preflight()
        finally:
            build._active_base_preflight = previous

    def test_material_receipt_detects_post_gate_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gate.json"
            path.write_bytes(b'{"verdict":"PASS"}\n')
            receipt = qualification._material(path, "gate result")
            path.write_bytes(b'{"verdict":"FAIL"}\n')
            with self.assertRaisesRegex(
                qualification.QualificationError, "material changed"
            ):
                qualification._require_material(receipt, "gate result")

    def test_verify_receipt_rejects_stale_run_id_before_material_use(self):
        value = {
            "schema": qualification.SCHEMA,
            "verdict": qualification.VERDICT,
            "build_allowed": True,
            "candidate": {
                "run_id": "ff" * 16,
                "profile": "E2",
                "source_contract_id": qualification.p280.CONTRACT_ID,
                "candidate_contract_sha256": "00" * 32,
            },
            "implementation": {},
            "gate_implementation": {},
            "gates": {},
            "safety": {},
        }
        value["payload_sha256"] = qualification.hashlib.sha256(
            qualification._canonical(value)
        ).hexdigest()
        with mock.patch.object(
            qualification,
            "_load_json",
            return_value=(
                value,
                {"path": "/tmp/q", "size": 1, "sha256": "00" * 32},
            ),
        ):
            with self.assertRaisesRegex(
                qualification.QualificationError, "identity mismatch"
            ):
                qualification.verify_receipt(
                    Path("unused"),
                    self.contract,
                    intent_path=Path("unused-intent"),
                    patch_path=Path("unused-patch"),
                )

    def test_repo_relative_binding_survives_namespace_rebase(self):
        left = Path("/tmp/left/repo")
        right = Path("/tmp/right/repo")
        self.assertEqual(
            qualification._repo_relative(
                left, left / "workspace/private/intent.json", "left"
            ),
            qualification._repo_relative(
                right, right / "workspace/private/intent.json", "right"
            ),
        )

    def test_qemu_command_rejects_version_query_substitution(self):
        with self.assertRaisesRegex(
            qualification.QualificationError, "command shape"
        ):
            qualification._qemu_command_semantics(
                ["/tools/usr/bin/qemu-system-aarch64", "--version"],
                {"kernel": "/kernel", "initramfs": "/initramfs"},
                "test QEMU",
            )

    def test_lifecycle_rejects_negative_timing_and_missing_digest(self):
        root = qualification.candidate_contract.intent.repo_root()
        source_receipts = {"source": {"size": 1, "sha256": "1" * 64}}
        material = {"path": "/private/material", "size": 1, "sha256": "2" * 64}
        binary_path = root / qualification.PINNED_QEMU_REPO_PATH
        binary = str(binary_path)
        build = {
            "checkpoint": material,
            "compile_output": "",
            "guest_config": "/private/config",
            "guest_config_sha256": qualification.kprobe_qemu.PINNED_CONFIG_SHA256,
            "harness": material,
            "init": material,
            "init_file": "ELF",
            "initramfs": material,
            "kernel": "/private/kernel",
            "kernel_sha256": qualification.kprobe_qemu.PINNED_KERNEL_SHA256,
            "runtime": material,
        }
        command = [
            binary,
            "-L",
            str(binary_path.parents[2] / "usr/share/qemu"),
            "-M",
            "virt",
            "-cpu",
            "cortex-a57",
            "-smp",
            "2",
            "-m",
            "512M",
            "-nographic",
            "-no-reboot",
            "-nic",
            "none",
            "-kernel",
            build["kernel"],
            "-initrd",
            build["initramfs"]["path"],
            "-append",
            qualification.QEMU_APPEND,
        ]
        sample = {
            "elapsed_sec": 2.0,
            "role_ns": 1,
            "bind_ns": 1,
            "console_sha256": "3" * 64,
            "verified": True,
        }
        value = {
            "schema": qualification.lifecycle_qemu.SCHEMA,
            "verdict": qualification.lifecycle_qemu.VERDICT,
            "source_contract_id": qualification.p280.CONTRACT_ID,
            "source_receipts": source_receipts,
            "cold_sample_count": 5,
            "samples": [copy.deepcopy(sample) for _index in range(5)],
            "command": command,
            "qemu_identity": {
                "binary": binary,
                "binary_sha256": qualification.kprobe_qemu.PINNED_QEMU_SHA256,
                "version": qualification.kprobe_qemu.PINNED_QEMU_VERSION,
            },
            "build": build,
            "scope": {
                "validated": qualification.LIFECYCLE_VALIDATED_SCOPE,
                "not_validated": qualification.LIFECYCLE_NOT_VALIDATED_SCOPE,
            },
        }
        receipt = {"path": str(root / "result.json"), "size": 1, "sha256": "4" * 64}
        for mutation in ("negative", "missing-digest"):
            changed = copy.deepcopy(value)
            if mutation == "negative":
                changed["samples"][0]["role_ns"] = -1
            else:
                changed["samples"][0].pop("console_sha256")
            with self.subTest(mutation=mutation), mock.patch.object(
                qualification, "_load_json", return_value=(changed, receipt)
            ), mock.patch.object(
                qualification.p280,
                "source_receipts",
                return_value=({}, source_receipts),
            ):
                with self.assertRaisesRegex(
                    qualification.QualificationError,
                    "sample 0",
                ):
                    qualification._verify_lifecycle_qemu(
                        root / "result.json", verify_materials=False
                    )
        changed = copy.deepcopy(value)
        changed["command"][0] = (
            "/untrusted/usr/bin/qemu-system-aarch64"
        )
        changed["command"][2] = "/untrusted/usr/share/qemu"
        with mock.patch.object(
            qualification, "_load_json", return_value=(changed, receipt)
        ), mock.patch.object(
            qualification.p280,
            "source_receipts",
            return_value=({}, source_receipts),
        ):
            with self.assertRaisesRegex(
                qualification.QualificationError,
                "binary identity differ",
            ):
                qualification._verify_lifecycle_qemu(
                    root / "result.json", verify_materials=False
                )

        with mock.patch.object(
            qualification, "_load_json", return_value=(value, receipt)
        ), mock.patch.object(
            qualification.p280,
            "source_receipts",
            return_value=({}, source_receipts),
        ):
            verified = qualification._verify_lifecycle_qemu(
                root / "result.json", verify_materials=False
            )
        self.assertNotIn("materials", verified)

        changed = copy.deepcopy(value)
        changed["unauthenticated"] = True
        with mock.patch.object(
            qualification, "_load_json", return_value=(changed, receipt)
        ), mock.patch.object(
            qualification.p280,
            "source_receipts",
            return_value=({}, source_receipts),
        ):
            with self.assertRaisesRegex(
                qualification.QualificationError, "not current"
            ):
                qualification._verify_lifecycle_qemu(
                    root / "result.json", verify_materials=False
                )

    def test_verify_receipt_executes_semantic_gate_revalidation(self):
        root = qualification.candidate_contract.intent.repo_root()
        intent_path = root / "workspace/private/intent.json"
        patch_path = root / "workspace/private/candidate.patch"
        intent_receipt = {"path": str(intent_path), "size": 1, "sha256": "5" * 64}
        patch_receipt = {
            "path": str(patch_path),
            "size": 7,
            "sha256": self.contract["patch"]["sha256"],
        }
        source_receipts = {}
        implementation = {
            "schema": "implementation",
            "verdict": qualification.p280.IMPLEMENTATION_VERDICT,
            "generated": {},
            "source_receipts": source_receipts,
            "verified": True,
        }
        gate_implementation = qualification._gate_implementation()
        gate_row = {
            "result": {"size": 1, "sha256": "6" * 64},
            "result_repo_path": "workspace/private/gate.json",
            "semantics": {},
            "verified": True,
        }
        safety = {"dictionary": {"safe": True}, "verified": True}
        value = {
            "schema": qualification.SCHEMA,
            "verdict": qualification.VERDICT,
            "build_allowed": True,
            "candidate": {
                "run_id": self.contract["run_id"],
                "profile": "E2",
                "source_contract_id": qualification.p280.CONTRACT_ID,
                "candidate_contract_sha256": qualification.hashlib.sha256(
                    qualification._canonical(self.contract)
                ).hexdigest(),
                "intent": intent_receipt,
                "intent_repo_path": qualification._repo_relative(
                    root, intent_path, "intent"
                ),
                "patch": patch_receipt,
                "patch_repo_path": qualification._repo_relative(
                    root, patch_path, "patch"
                ),
            },
            "implementation": implementation,
            "gate_implementation": gate_implementation,
            "gates": {
                "userspace": copy.deepcopy(gate_row),
                "safety": safety,
                "p260_generic_qemu": copy.deepcopy(gate_row),
                "kprobe_control_qemu": copy.deepcopy(gate_row),
                "trace_lifecycle_qemu": copy.deepcopy(gate_row),
            },
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
        value["payload_sha256"] = qualification.hashlib.sha256(
            qualification._canonical(value)
        ).hexdigest()

        def selected_material(path, _label):
            return intent_receipt if path == intent_path else patch_receipt

        with mock.patch.object(
            qualification,
            "_load_json",
            return_value=(
                value,
                {"path": str(root / "qualification.json"), "size": 1, "sha256": "7" * 64},
            ),
        ), mock.patch.object(
            qualification, "_material", side_effect=selected_material
        ), mock.patch.object(
            qualification.p280,
            "implementation_result",
            return_value=implementation,
        ), mock.patch.object(
            qualification.p280,
            "source_receipts",
            return_value=({}, source_receipts),
        ), mock.patch.object(
            qualification,
            "_gate_implementation",
            return_value=gate_implementation,
        ), mock.patch.object(
            qualification,
            "_expected_safety",
            return_value={"safe": True},
        ), mock.patch.object(
            qualification,
            "_verify_userspace",
            side_effect=qualification.QualificationError(
                "semantic revalidation reached"
            ),
        ):
            with self.assertRaisesRegex(
                qualification.QualificationError,
                "semantic revalidation reached",
            ):
                qualification.verify_receipt(
                    root / "qualification.json",
                    self.contract,
                    intent_path=intent_path,
                    patch_path=patch_path,
                )

    def test_qualification_rejects_extra_top_level_or_gate_field(self):
        path = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p280_v5/"
            "pre-lto-qualification.json"
        )
        value = qualification.json.loads(path.read_text(encoding="ascii"))
        receipt = qualification._material(path, "qualification")
        for mutation in ("top-level", "stored-gate"):
            changed = copy.deepcopy(value)
            if mutation == "top-level":
                changed["unauthenticated"] = True
            else:
                changed["gates"]["kprobe_control_qemu"]["materials"] = []
            payload = dict(changed)
            payload.pop("payload_sha256")
            changed["payload_sha256"] = qualification.hashlib.sha256(
                qualification._canonical(payload)
            ).hexdigest()
            with self.subTest(mutation=mutation):
                if mutation == "stored-gate":
                    with self.assertRaisesRegex(
                        qualification.QualificationError,
                        "stored gate is invalid",
                    ):
                        qualification._same_gate(
                            changed["gates"]["kprobe_control_qemu"],
                            value["gates"]["kprobe_control_qemu"],
                            "test",
                        )
                else:
                    with mock.patch.object(
                        qualification,
                        "_load_json",
                        return_value=(changed, receipt),
                    ):
                        with self.assertRaisesRegex(
                            qualification.QualificationError,
                            "schema is not exact",
                        ):
                            qualification.verify_receipt(
                                path,
                                self.contract,
                                intent_path=ROOT / "unused-intent",
                                patch_path=ROOT / "unused-patch",
                            )

    def test_qemu_binary_requires_pinned_repo_path_and_current_bytes(self):
        command = [
            "/tmp/fake/usr/bin/qemu-system-aarch64",
        ]
        with self.assertRaisesRegex(
            qualification.QualificationError, "path is not pinned"
        ):
            qualification._verify_current_qemu_binary(
                command, ROOT, "test QEMU"
            )
        command[0] = str(ROOT / qualification.PINNED_QEMU_REPO_PATH)
        with mock.patch.object(
            qualification,
            "_material",
            return_value={"path": command[0], "size": 1, "sha256": "0" * 64},
        ):
            with self.assertRaisesRegex(
                qualification.QualificationError, "not pinned"
            ):
                qualification._verify_current_qemu_binary(
                    command, ROOT, "test QEMU"
                )


if __name__ == "__main__":
    unittest.main()
