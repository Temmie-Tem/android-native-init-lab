from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p282_pre_lto_qualification as p282q  # noqa: E402
import s22plus_fyg8_p284_pre_lto_qualification as p284q  # noqa: E402
import s22plus_fyg8_p284_source_contract as p284  # noqa: E402


class P284QualificationTests(unittest.TestCase):
    def _write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )

    def _prepare_ingestion_root(
        self, root: Path, value: dict
    ) -> Path:
        for relative in (
            p284q.ingestion.DEFAULT_RUNTIME_SOURCE,
            p284q.ingestion.DEFAULT_P282_RUNTIME_SOURCE,
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        result = (
            root
            / "workspace/private/outputs/p284-ingestion/result.json"
        )
        self._write_json(result, value)
        return result

    def _evidence(self) -> dict[str, dict]:
        dependencies = (
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
            ("sysfs_ingestion",),
        )
        return {
            name: {"verified": True}
            for row in dependencies
            for name in row
        }

    def test_gate_inventory_is_versioned_20_over_historical_19(self) -> None:
        self.assertEqual(len(p282q.GATE_NAMES), 19)
        self.assertEqual(len(p284q.GATE_NAMES), 20)
        rows = p284q._gate_matrix(self._evidence())
        self.assertEqual([row["ordinal"] for row in rows], list(range(1, 21)))
        self.assertEqual(rows[-1]["evidence"], ["sysfs_ingestion"])

    def test_base_context_binds_and_restores_versioned_contract(self) -> None:
        historical = (p282q.p282, p282q.SCHEMA, p282q.VERDICT)
        with p284q._base_context():
            self.assertIs(p282q.p282, p284)
            self.assertEqual(p282q.SCHEMA, p284q.SCHEMA)
        self.assertEqual((p282q.p282, p282q.SCHEMA, p282q.VERDICT), historical)

    def test_gate_implementation_binds_p284_closure(self) -> None:
        implementation = p284q._gate_implementation()
        self.assertEqual(
            implementation["closure"]["path"],
            (
                "workspace/public/src/scripts/revalidation/"
                "s22plus_fyg8_p284_e2_stock_closure.py"
            ),
        )
        self.assertEqual(
            implementation["p284_sysfs_ingestion_oracle"]["path"],
            (
                "workspace/public/src/scripts/revalidation/"
                "s22plus_fyg8_p284_sysfs_ingestion_oracle.py"
            ),
        )

    def test_current_source_bound_ingestion_receipt_verifies(self) -> None:
        result = p284q._verify_ingestion_oracle(
            ROOT / p284q.DEFAULT_INGESTION_RESULT
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["schema"], p284q.ingestion.SCHEMA)

    def test_p284_qualification_does_not_accept_p282_identity(self) -> None:
        self.assertNotEqual(p284q.SCHEMA, p282q.SCHEMA)
        self.assertNotEqual(p284.CONTRACT_ID, p282q.p282.CONTRACT_ID)
        value = {
            "build_allowed": True,
            "candidate": {},
            "evidence": {},
            "gate_implementation": {},
            "gates": [],
            "implementation": {},
            "safety": {},
            "schema": p284q.SCHEMA,
            "verdict": p284q.VERDICT,
        }
        value["payload_sha256"] = hashlib.sha256(
            p284q.base._canonical(value)
        ).hexdigest()
        with tempfile.TemporaryDirectory(
            prefix="p284-p282-injection-",
            dir=ROOT / "workspace/private",
        ) as raw:
            path = Path(raw) / "qualification.json"
            self._write_json(path, value)
            with self.assertRaisesRegex(
                p284q.QualificationError,
                "qualification header is invalid",
            ):
                p284q.verify_receipt(
                    path,
                    {
                        "run_id": "11" * 16,
                        "source_contract_id": p282q.p282.CONTRACT_ID,
                    },
                    intent_path=ROOT / "unused-intent",
                    patch_path=ROOT / "unused-patch",
                )

    def test_ingestion_evidence_is_portable_across_repo_copies(self) -> None:
        value = json.loads(
            (ROOT / p284q.DEFAULT_INGESTION_RESULT).read_text(
                encoding="ascii"
            )
        )
        verified = []
        with tempfile.TemporaryDirectory(
            prefix="p284-portable-a-"
        ) as raw_a, tempfile.TemporaryDirectory(
            prefix="p284-portable-b-"
        ) as raw_b:
            for raw in (raw_a, raw_b):
                root = Path(raw)
                path = self._prepare_ingestion_root(root, value)
                with mock.patch.object(
                    p284q.candidate_contract.intent,
                    "repo_root",
                    return_value=root,
                ):
                    row = p284q._verify_ingestion_oracle(
                        path, verify_materials=False
                    )
                verified.append(p284q.base._portable_repo_paths(root, row))
        self.assertEqual(verified[0], verified[1])
        self.assertEqual(
            verified[0]["result_repo_path"],
            "workspace/private/outputs/p284-ingestion/result.json",
        )
        self.assertEqual(
            verified[0]["result"]["path"],
            "workspace/private/outputs/p284-ingestion/result.json",
        )

    def test_ingestion_receipt_tampering_is_rejected(self) -> None:
        value = json.loads(
            (ROOT / p284q.DEFAULT_INGESTION_RESULT).read_text(
                encoding="ascii"
            )
        )
        value["runtime_sources"]["p260"]["sha256"] = "00" * 32
        with tempfile.TemporaryDirectory(
            prefix="p284-tamper-",
            dir=ROOT / "workspace/private",
        ) as raw:
            path = Path(raw) / "result.json"
            self._write_json(path, value)
            with self.assertRaisesRegex(
                p284q.QualificationError,
                "runtime source binding changed",
            ):
                p284q._verify_ingestion_oracle(
                    path, verify_materials=False
                )

    def test_ingestion_receipt_rejects_runtime_source_mutation(self) -> None:
        value = json.loads(
            (ROOT / p284q.DEFAULT_INGESTION_RESULT).read_text(
                encoding="ascii"
            )
        )
        with tempfile.TemporaryDirectory(
            prefix="p284-runtime-mutation-"
        ) as raw:
            root = Path(raw)
            path = self._prepare_ingestion_root(root, value)
            runtime = root / p284q.ingestion.DEFAULT_RUNTIME_SOURCE
            runtime.write_bytes(runtime.read_bytes() + b"\n")
            with mock.patch.object(
                p284q.candidate_contract.intent,
                "repo_root",
                return_value=root,
            ), self.assertRaisesRegex(
                p284q.QualificationError,
                "runtime source binding changed",
            ):
                p284q._verify_ingestion_oracle(
                    path, verify_materials=False
                )

    def test_p282_receipt_cannot_fill_p284_ingestion_gate(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="p284-p282-receipt-",
            dir=ROOT / "workspace/private",
        ) as raw:
            path = Path(raw) / "result.json"
            self._write_json(
                path,
                {
                    "schema": p282q.SCHEMA,
                    "verdict": p282q.VERDICT,
                    "verified": True,
                },
            )
            with self.assertRaisesRegex(
                p284q.QualificationError,
                "ingestion result is incomplete",
            ):
                p284q._verify_ingestion_oracle(
                    path, verify_materials=False
                )


if __name__ == "__main__":
    unittest.main()
