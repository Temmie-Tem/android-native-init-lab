#!/usr/bin/env python3
"""Registration tests for the exact P2.82 build and packaging path."""

from __future__ import annotations

import argparse
import copy
import hashlib
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

import build_s22plus_fyg8_p234_candidate as candidate  # noqa: E402
import s22plus_fyg8_p234_build as build  # noqa: E402
import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p280_source_contract as p280  # noqa: E402
import s22plus_fyg8_p282_linked_audit as linked  # noqa: E402
import s22plus_fyg8_p282_pre_lto_qualification as p282q  # noqa: E402
import s22plus_fyg8_p282_source_contract as p282  # noqa: E402


class QualificationError(ValueError):
    pass


class P282BuildRegistrationTests(unittest.TestCase):
    def setUp(self):
        build._bound_pre_lto_qualification = None
        build._bound_pre_lto_provenance_key = None
        build._ContractAdapter._bound_result = None
        self.contract = {
            "schema": p282.CONTRACT_SCHEMA,
            "verdict": p282.CONTRACT_VERDICT,
            "verified": True,
            "profile": "E2",
            "source_contract_id": p282.CONTRACT_ID,
            "run_id": "82" * 16,
            "patch": {"size": 7, "sha256": "2" * 64},
            "base_files": {},
            "patched_files": {},
        }

    def _args(self, qualification_path: Path | None) -> argparse.Namespace:
        return argparse.Namespace(
            work_tree=Path("source"),
            intent=Path("intent.json"),
            patch=Path("candidate.patch"),
            pre_lto_qualification=qualification_path,
        )

    def _qualification_module(self, summary):
        return SimpleNamespace(
            __name__=build.QUALIFICATION_MODULES[p282.CONTRACT_ID][0],
            p282=SimpleNamespace(CONTRACT_ID=p282.CONTRACT_ID),
            SCHEMA="p282-qualification-schema",
            VERDICT="p282-qualification-verdict",
            QualificationError=QualificationError,
            verify_receipt=mock.Mock(return_value=summary),
        )

    def test_build_selects_exact_p282_qualification_without_fallback(self):
        summary = {
            "schema": "p282-qualification-schema",
            "verdict": "p282-qualification-verdict",
            "build_allowed": True,
            "run_id": self.contract["run_id"],
            "source_contract_id": p282.CONTRACT_ID,
            "verified": True,
        }
        qualification = self._qualification_module(summary)
        with mock.patch.object(
            build.candidate_contract, "verify", return_value=self.contract
        ), mock.patch.object(
            build.importlib, "import_module", return_value=qualification
        ) as importer:
            result = build._configure_contract(
                self._args(Path("workspace/private/p282-qualification.json"))
            )
        self.assertIs(result, self.contract)
        importer.assert_called_once_with(
            "s22plus_fyg8_p282_pre_lto_qualification"
        )
        self.assertEqual(build._bound_pre_lto_qualification, summary)
        self.assertEqual(
            build._bound_pre_lto_provenance_key,
            "p282_pre_lto_qualification",
        )

    def test_build_rejects_missing_or_mismatched_p282_qualification(self):
        with mock.patch.object(
            build.candidate_contract, "verify", return_value=self.contract
        ):
            with self.assertRaisesRegex(
                build.BuildError, "requires --pre-lto-qualification"
            ):
                build._configure_contract(self._args(None))

        wrong = self._qualification_module({})
        wrong.p282.CONTRACT_ID = p280.CONTRACT_ID
        with mock.patch.object(
            build.candidate_contract, "verify", return_value=self.contract
        ), mock.patch.object(
            build.importlib, "import_module", return_value=wrong
        ):
            with self.assertRaisesRegex(
                build.BuildError, "module contract mismatch"
            ):
                build._configure_contract(
                    self._args(Path("workspace/private/q.json"))
                )

        with mock.patch.object(
            build.candidate_contract, "verify", return_value=self.contract
        ), mock.patch.object(
            build.importlib,
            "import_module",
            side_effect=ModuleNotFoundError("p282 qualification absent"),
        ):
            with self.assertRaisesRegex(
                build.BuildError, "qualification module unavailable"
            ):
                build._configure_contract(
                    self._args(Path("workspace/private/q.json"))
                )

    def test_preflight_emits_only_p282_provenance_key(self):
        summary = {
            "build_allowed": True,
            "verified": True,
            "source_contract_id": p282.CONTRACT_ID,
        }
        build._ContractAdapter._bound_result = self.contract
        build._bound_pre_lto_qualification = summary
        build._bound_pre_lto_provenance_key = (
            "p282_pre_lto_qualification"
        )
        previous = build._active_base_preflight
        try:
            build._active_base_preflight = lambda *_args, **_kwargs: {
                "build_allowed": True,
                "provenance": {},
            }
            result = build.qualified_preflight()
        finally:
            build._active_base_preflight = previous
        self.assertEqual(
            result["provenance"],
            {"p282_pre_lto_qualification": summary},
        )

    def test_repro_verifies_exact_p282_qualification_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            intent = repository / "workspace/private/intent.json"
            patch = repository / "workspace/private/candidate.patch"
            qualification_path = (
                repository / "workspace/private/qualification.json"
            )
            intent.parent.mkdir(parents=True)
            intent.write_bytes(b"intent\n")
            patch.write_bytes(b"patch\n")
            payload = b'{"qualification":"p282"}\n'
            qualification_path.write_bytes(payload)
            gate_evidence = {
                name: {
                    "result": {
                        "size": index,
                        "sha256": f"{index:064x}",
                    }
                }
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
                )
            }
            summary = {
                "schema": "p282-qualification-schema",
                "verdict": "p282-qualification-verdict",
                "build_allowed": True,
                "run_id": self.contract["run_id"],
                "source_contract_id": p282.CONTRACT_ID,
                "qualification_repo_path": (
                    "workspace/private/qualification.json"
                ),
                "intent_repo_path": "workspace/private/intent.json",
                "patch_repo_path": "workspace/private/candidate.patch",
                "qualification": {
                    "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                },
                "gate_result_receipts": p282q._gate_result_receipts(
                    gate_evidence
                ),
                "verified": True,
            }
            qualification = self._qualification_module(summary)
            with mock.patch.object(
                repro.importlib,
                "import_module",
                return_value=qualification,
            ):
                result = repro.verify_p282_qualification_file(
                    summary,
                    self.contract,
                    intent_path=intent,
                    patch_path=patch,
                    root=repository,
                )
            self.assertEqual(result, summary)
            qualification.verify_receipt.assert_called_once_with(
                qualification_path,
                self.contract,
                intent_path=intent,
                patch_path=patch,
            )

            stale = copy.deepcopy(summary)
            stale["qualification"]["sha256"] = "f" * 64
            with self.assertRaisesRegex(
                repro.CheckError, "file receipt mismatch"
            ):
                repro.verify_p282_qualification_file(
                    stale,
                    self.contract,
                    intent_path=intent,
                    patch_path=patch,
                    root=repository,
                )

    def test_linked_adapter_registry_is_exact_and_p280_is_preserved(self):
        self.assertEqual(
            repro.LINKED_VALIDATOR_ADAPTERS[p282.CONTRACT_ID],
            "s22plus_fyg8_p282_linked_audit",
        )
        self.assertEqual(
            linked.EXPECTED_SOURCE_CONTRACT_ID, p282.CONTRACT_ID
        )
        self.assertEqual(
            repro.LINKED_VALIDATOR_ADAPTERS[p280.CONTRACT_ID],
            "s22plus_fyg8_p280_linked_audit",
        )

    def test_candidate_safety_uses_exact_p282_authority(self):
        safety = candidate.artifact_safety(
            {
                "profile": "E2",
                "source_contract_id": p282.CONTRACT_ID,
            }
        )
        for name, value in candidate.p282_spec.RUNTIME_AUTHORITY.items():
            self.assertEqual(safety[name], value)
        self.assertFalse(safety["host_role_authority"])
        historical = candidate.artifact_safety(
            {
                "profile": "E2",
                "source_contract_id": p280.CONTRACT_ID,
            }
        )
        self.assertEqual(
            {
                name: historical[name]
                for name in candidate.p280_spec.RUNTIME_AUTHORITY
            },
            candidate.p280_spec.RUNTIME_AUTHORITY,
        )

    def test_candidate_repro_requires_p282_adapter_and_qualification(self):
        image = {"size": 123, "sha256": "a" * 64}
        value = {
            "schema": repro.SCHEMA,
            "target": candidate.TARGET,
            "verdict": repro.VERDICT,
            "candidate_contract": self.contract,
            "linked_audit": {
                "verified": True,
                "audit_adapter": linked.ADAPTER_ID,
                "source_contract_validator": {
                    "writer_guard": {
                        "guard_dominates_retained_stores": True
                    }
                },
            },
            "byte_identical_artifacts": {
                name: True
                for name in repro.ARTIFACT_LIMITS
                if name != "build-result.json"
            },
            "build_a": {"artifacts": {"Image": image}},
            "pre_lto_qualification": {
                "verified": True,
                "source_contract_id": p282.CONTRACT_ID,
            },
        }
        with mock.patch.object(
            candidate,
            "_read_json",
            return_value=(value, {"size": 1, "sha256": "b" * 64}),
        ), mock.patch.object(
            repro,
            "verify_p282_qualification_file",
            return_value=value["pre_lto_qualification"],
        ) as verify:
            result = candidate.verify_repro_result(
                Path("unused"),
                image,
                self.contract,
                intent_path=ROOT / "workspace/private/intent.json",
                patch_path=ROOT / "workspace/private/candidate.patch",
            )
        self.assertTrue(result["linked_audit_verified"])
        verify.assert_called_once()

        changed = copy.deepcopy(value)
        changed["linked_audit"]["audit_adapter"] = (
            "s22plus-fyg8-p280-linked-audit-v1"
        )
        with mock.patch.object(
            candidate,
            "_read_json",
            return_value=(changed, {"size": 1, "sha256": "b" * 64}),
        ), self.assertRaisesRegex(
            candidate.BuildError, "P2.82 linked audit adapter mismatch"
        ):
            candidate.verify_repro_result(
                Path("unused"),
                image,
                self.contract,
                intent_path=ROOT / "workspace/private/intent.json",
                patch_path=ROOT / "workspace/private/candidate.patch",
            )


if __name__ == "__main__":
    unittest.main()
