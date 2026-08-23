from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(REVALIDATION))
QUALIFIER = REVALIDATION / "s22plus_fyg8_p319_candidate_qualification.py"
RAW_AUDITOR = REVALIDATION / "s22plus_fyg8_raw_first_observer_audit.py"
BASE = ROOT / "workspace/private/outputs/s22plus_fyg8_p319"
PHASE1 = BASE / "stock-witness-runtime-v1-20260821-52"
PHASE2 = BASE / "stock-witness-runtime-v1-20260821-53"
OLD_PHASE2 = BASE / "stock-witness-runtime-v1-20260821-49"
RUN = BASE / "candidate-qualification-v1-20260821-10"
INTERMEDIATE_RUN = BASE / "candidate-qualification-v1-20260821-09"
RAW_RECEIPT = BASE / "raw-first-observer-audit-20260823-04-candidate-requalification.json"
EXECUTABILITY = BASE / "experiment-executability-closure-v1-20260823-03/result.json"
PREREQUISITE = BASE / "process-v2-prerequisite-audit-20260823-03.json"
INTEGRATION = BASE / "process-v2-integration-qualification-v1-20260823-04/result.json"
INTERMEDIATE_INTEGRATION = BASE / "process-v2-integration-qualification-v1-20260823-03/result.json"
REPORT = ROOT / "docs/reports/S22PLUS_FYG8_P319_CANDIDATE_REQUALIFICATION_H0_2026-08-23.md"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P319CandidateRequalificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qualifier = load(QUALIFIER, "p319_candidate_requalification_test")
        cls.raw_auditor = load(RAW_AUDITOR, "p319_raw_requalification_test")
        cls.intent_bytes = (RUN / "intent.json").read_bytes()
        cls.intent = json.loads(cls.intent_bytes)
        cls.qualification = json.loads((RUN / "qualification.json").read_bytes())
        cls.integration_bytes = INTEGRATION.read_bytes()
        cls.integration = json.loads(cls.integration_bytes)

    def test_final_private_receipts_are_exact_mode0400_single_link(self):
        expected = {
            PHASE1 / "result.json": (382264, "982f903f7685f63e5b2fbadebc5a3bbef5d98f009207ac352bda80777b09e886"),
            PHASE2 / "result.json": (392886, "21beec5d2010ecb5804c09055c93a24f83f0fc4be0c9125d24a831908efeaa4a"),
            RUN / "intent.json": (107403, "5a6a24195d89743b7b71e3dbd8db2d8d263c129b774d4a1d6155704507cb3bb2"),
            RUN / "static-reconstruction.json": (975, "ce271a46e4bef9510e409c92dd29aded83f39dbcb4cec289c16897f6007d10af"),
            RUN / "qualification.json": (113386, "72b39572318945a180dff396998c8f2d72babc89a0f8655557a0dfc000cc852d"),
            RUN / "report.json": (16229, "2f49b75230088c14e6f784e02e9297a94da6d4a47c6ebc8bcdbc9e9e0e5853f9"),
            RAW_RECEIPT: (11012, "ac3876c078062098ce240ae78c102ae19d2fe1b47eba257d374131cbaffc193e"),
            EXECUTABILITY: (96194, "636cb0cd551254c32120e31af8765b692f964256ca7e380f69b79c170df5b542"),
            PREREQUISITE: (12537, "ee6a1e79dfcd155f5bcdec95fbea61eea0c0645a8cd3ea2c7d30a04b59d7837c"),
            INTEGRATION: (61388, "745814926e44763214ed15d3eeb10d2a4c4e8bb591d3b92d96685aa4cf4aff88"),
        }
        for path, (size, digest) in expected.items():
            with self.subTest(path=path.name):
                payload = path.read_bytes()
                info = path.stat()
                self.assertEqual(len(payload), size)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
                self.assertEqual(info.st_nlink, 1)

    def test_intent_binds_the_current_437_key_source_closure(self):
        current = self.qualifier._source_keys()
        self.assertEqual(self.intent["source_keys"], current)
        self.assertEqual(len(current), 437)
        canonical = json.dumps(
            current,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(),
            "f41bfd2d1a4cf62aa62500a636a22e2035f3d56f9151e806e80da86f6c9cdded",
        )
        self.assertEqual(
            current["qualification_source"],
            {
                "logical_path": "workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_candidate_qualification.py",
                "size": 47599,
                "sha256": "2618c9c9ad0723ce456fcf718af0f456e02e020acc52c27864b501a0fd42ace4",
            },
        )
        self.assertEqual(self.intent["module_plan"]["count"], 73)
        self.assertEqual(self.intent["module_plan"]["eud_index"], 38)
        self.assertEqual(
            self.intent["planned_outputs"],
            {
                "phase1": "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-52",
                "phase2": "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-53",
            },
        )
        self.assertEqual(self.qualifier.DEFAULT_PHASE1.name, "stock-witness-runtime-v1-20260821-50")
        self.assertEqual(self.qualifier.DEFAULT_PHASE2.name, "stock-witness-runtime-v1-20260821-51")
        self.assertEqual(self.qualifier.DEFAULT_RUN_ROOT.name, "candidate-qualification-v1-20260821-09")

    def test_final_candidate_and_userspace_bytes_are_unchanged(self):
        for relative in (
            "candidate-a/boot.img",
            "candidate-a/boot.img.lz4",
            "candidate-a/odin4/AP.tar.md5",
            "userspace-a/init",
            "userspace-a/s22-e1-child",
        ):
            with self.subTest(relative=relative):
                self.assertEqual(
                    (PHASE2 / relative).read_bytes(),
                    (OLD_PHASE2 / relative).read_bytes(),
                )

    def test_final_qualification_is_exactly_regenerable(self):
        value = self.qualifier.audit_existing(RUN, PHASE1, PHASE2)
        self.assertTrue(value["audit_only"])
        self.assertFalse(value["scope"]["device_contact"])
        self.assertFalse(value["scope"]["live_authorized"])
        self.assertFalse(value["process_v2_ready_created"])

    def test_raw_first_registration_is_exact_and_stays_restrictive(self):
        source = QUALIFIER.read_text(encoding="utf-8")
        value = self.raw_auditor._audit_host_only_non_acquiring_source(
            QUALIFIER.name, source
        )
        self.assertEqual(value["size"], 47599)
        self.assertEqual(
            value["sha256"],
            "2618c9c9ad0723ce456fcf718af0f456e02e020acc52c27864b501a0fd42ace4",
        )
        self.assertEqual(value["exec_lines"], [238, 252])
        self.assertEqual(value["getattr_line"], 152)
        with self.assertRaises(self.raw_auditor.RawFirstAuditError):
            self.raw_auditor._audit_host_only_non_acquiring_source(
                QUALIFIER.name,
                source.replace('"device_contact": False', '"device_contact": True', 1),
            )

    def test_integration_has_only_the_fresh_baseline_machine_blocker(self):
        self.assertEqual(
            self.integration["verdict"],
            "BLOCKED_P319_PROCESS_V2_INTEGRATION_H0",
        )
        self.assertEqual(
            self.integration["blockers"],
            [{"code": "FRESH_BASELINE_MISSING", "detail": "fresh baseline is unavailable"}],
        )
        comparison = self.integration["components"]["adapter_pin"]["source_keys"]
        self.assertEqual(comparison["mismatch_count"], 0)
        self.assertEqual(comparison["mismatch_keys"], [])
        self.assertTrue(comparison["exact_match"])
        self.assertTrue(self.integration["source_closure_pass"])
        self.assertTrue(self.integration["global_consumed_candidate_registry_present"])
        self.assertTrue(self.integration["runner_recovery_closed"])
        for key in (
            "runner_ready",
            "ready",
            "ready_manifest_created",
            "run_manifest_created",
            "approval_created",
            "d0_authorized",
            "d1_authorized",
            "f1_authorized",
            "replay_authorized",
            "causal_result_allowed",
            "candidate_success",
            "device_contact",
            "live_authorized",
        ):
            with self.subTest(key=key):
                self.assertFalse(self.integration[key])

    def test_fail_closed_intermediate_is_preserved_not_rewritten(self):
        self.assertTrue(INTERMEDIATE_RUN.is_dir())
        payload = INTERMEDIATE_INTEGRATION.read_bytes()
        self.assertEqual(len(payload), 50490)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "caf04f34a6a8f985e73bb2acc5f79a7fd350f8cd3d9433cb368cc1dd5eef45e0",
        )
        value = json.loads(payload)
        self.assertIn(
            "PREREQUISITE_BLOCKED",
            {item["code"] for item in value["blockers"]},
        )
        self.assertNotIn(
            "REQUALIFICATION_REQUIRED",
            {item["code"] for item in value["blockers"]},
        )

    def test_report_goal_and_ledger_keep_review_and_authority_boundaries(self):
        report = REPORT.read_text(encoding="utf-8")
        goal = GOAL.read_text(encoding="utf-8")
        ledger = LEDGER.read_text(encoding="utf-8")
        self.assertIn(
            "Status: `PASS_GO_P319_CANDIDATE_REQUALIFICATION_H0_CAPABILITY_V1`",
            report,
        )
        self.assertIn("exactly one machine\nblocker: `FRESH_BASELINE_MISSING`", report)
        self.assertIn("Topic 33", report)
        self.assertIn("topic 34", report)
        self.assertIn("`-52`/`-53`/`-10`", goal)
        implementation_rows = [
            line
            for line in ledger.splitlines()
            if "| h0-candidate-requalification-34 |" in line
        ]
        review_rows = [
            line
            for line in ledger.splitlines()
            if "| h0-candidate-requalification-review-34 |" in line
        ]
        self.assertEqual(len(implementation_rows), 1)
        self.assertEqual(len(review_rows), 1)
        self.assertIn(
            "P319_CANDIDATE_REQUALIFICATION_IMPLEMENTED_REVIEW_PENDING",
            implementation_rows[0],
        )
        self.assertNotIn("PASS_GO_", implementation_rows[0])
        self.assertIn("52/36/16", implementation_rows[0])
        self.assertIn(
            "PASS_GO_P319_CANDIDATE_REQUALIFICATION_H0_CAPABILITY_V1",
            review_rows[0],
        )
        self.assertIn("56/37/19", review_rows[0])


if __name__ == "__main__":
    unittest.main()
