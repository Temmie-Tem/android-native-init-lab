import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_s22plus_fyg8_p318_candidate as candidate  # noqa: E402
import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as runner  # noqa: E402
import s22plus_fyg8_p317_generator as p317_generator  # noqa: E402
import s22plus_fyg8_p318_e2_stock_closure as stock  # noqa: E402
import s22plus_fyg8_p318_generator as generator  # noqa: E402
import s22plus_fyg8_p318_overlay_contract as overlay  # noqa: E402
import s22plus_fyg8_p318_qualification_closure as qualification  # noqa: E402
import s22plus_fyg8_p318_candidate_static_checker as static_checker  # noqa: E402


class P318PackagingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_id, cls.unsat_tag, cls.profile = generator.frozen_identity(ROOT)
        cls.generated = generator.generate_bytes(
            ROOT, run_id=cls.run_id, unsat_tag=cls.unsat_tag, profile=cls.profile
        )

    def test_70_row_plan_is_exact_69_stock_plus_latch(self):
        plan = self.generated["plan_header"]
        self.assertEqual(plan.count(b'.ko"'), 70)
        self.assertEqual(plan.count(stock.LATCH_ROW), 1)
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "plan.h"
            path.write_bytes(plan)
            projected = stock._stock_plan(path)  # noqa: SLF001
        parent = p317_generator.generate_bytes(
            ROOT, run_id=self.run_id, unsat_tag=self.unsat_tag, profile=self.profile
        )["plan_header"]
        self.assertEqual(projected, parent)

    def test_custom_module_identities_match_built_bytes(self):
        paths = (
            (
                candidate.DEFAULT_LATCH,
                421872,
                "52f2e59aae62224c772b0a86a908ae50b6b7b174aa258459ff170c7c703a683c",
            ),
            (
                candidate.DEFAULT_DIAGNOSTIC,
                303112,
                "d7dac722a11b2df932083bc16a6fac209ef1d90654d529b25391d85c6e1dec85",
            ),
        )
        for relative, size, digest in paths:
            payload = (ROOT / relative).read_bytes()
            self.assertEqual(len(payload), size)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)

    def test_candidate_semantics_require_both_modules_and_no_old_diag(self):
        pre = {"size": 1, "sha256": "a" * 64}
        identities = {
            "early_latch": {"size": 1, "sha256": "b" * 64},
            "late_diagnostic": {"size": 2, "sha256": "c" * 64},
        }
        value = {
            "schema": qualification.CANDIDATE_SCHEMA,
            "verdict": qualification.CANDIDATE_VERDICT,
            "prepackaging_closure": pre,
            "candidate_contract": {"module_identities": identities},
            "construction": {
                "latch_staged_path": candidate.LATCH_RAMDISK_PATH,
                "diagnostic_staged_path": candidate.DIAGNOSTIC_RAMDISK_PATH,
                "latch_staged_exactly_once": True,
                "diagnostic_staged_exactly_once": True,
                "both_custom_modules_absent_from_base": True,
                "diagnostic_absent_from_early_plan": True,
                "old_p317_diagnostic_absent": True,
                "latch_module": identities["early_latch"],
                "diagnostic_module": identities["late_diagnostic"],
            },
            "safety": {
                "boot_only_ap": True,
                "fixed_p310_image": True,
                "custom_module_binaries_injected": 2,
                "effective_early_module_count": 70,
                "device_contact": False,
            },
        }
        qualification._validate_candidate_result(  # noqa: SLF001
            value, prepackaging_receipt=pre
        )
        value["construction"]["old_p317_diagnostic_absent"] = False
        with self.assertRaises(qualification.QualificationError):
            qualification._validate_candidate_result(  # noqa: SLF001
                value, prepackaging_receipt=pre
            )

    def test_successor_authority_replaces_the_p316_operational_count_set(self):
        p316 = stock.base.base
        previous = p316.P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS
        self.assertNotIn(
            stock.P317_RETIRED_DIAGNOSTIC_PATH,
            stock.P318_OPERATIONAL_ABSOLUTE_PATH_STRINGS,
        )
        self.assertTrue(
            stock.P318_AUTHORITY_PATHS
            <= stock.P318_OPERATIONAL_ABSOLUTE_PATH_STRINGS
        )
        with stock.exact_init_authority(b"not-consumed-by-this-context-test"):
            self.assertEqual(
                p316.P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS,
                stock.P318_OPERATIONAL_ABSOLUTE_PATH_STRINGS,
            )
        self.assertEqual(p316.P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS, previous)

    def test_process_v2_selects_the_p318_overlay_and_rootfs_authorities(self):
        self.assertIs(
            evidence._select_e2_closure(  # noqa: SLF001
                evidence.P310_SOURCE_CONTRACT_ID,
                evidence.P318_MAX77705_OVERLAY_CONTRACT_ID,
            ),
            stock,
        )
        with self.assertRaises(evidence.EvidenceError):
            evidence._select_e2_closure(  # noqa: SLF001
                evidence.P300_SOURCE_CONTRACT_ID,
                evidence.P318_MAX77705_OVERLAY_CONTRACT_ID,
            )
        sentinel = {"verified": True}
        previous = overlay.verify_intent
        overlay.verify_intent = lambda _root, _intent: sentinel
        try:
            self.assertIs(
                evidence._validate_userspace_overlay_contract(  # noqa: SLF001
                    sentinel, evidence.P318_MAX77705_OVERLAY_CONTRACT_ID
                ),
                sentinel,
            )
            with self.assertRaises(evidence.EvidenceError):
                evidence._validate_userspace_overlay_contract(  # noqa: SLF001
                    {"verified": False},
                    evidence.P318_MAX77705_OVERLAY_CONTRACT_ID,
                )
        finally:
            overlay.verify_intent = previous

    def test_process_v2_registers_the_exact_p318_static_contract(self):
        self.assertEqual(
            evidence.P318_CANDIDATE_STATIC_SCHEMA, static_checker.SCHEMA
        )
        self.assertEqual(
            evidence.P318_CANDIDATE_STATIC_VERDICT, static_checker.VERDICT
        )
        self.assertEqual(evidence.P318_CANDIDATE_STATIC_MAX_BYTES, 2 * 1024 * 1024)
        self.assertEqual(
            runner._overridden_candidate_sources(  # noqa: SLF001
                evidence.P318_MAX77705_OVERLAY_CONTRACT_ID
            ),
            frozenset({"p310_telemetry_decoder"}),
        )

    def test_live_endpoint_transition_classifier_is_a_frozen_source_key(self):
        self.assertEqual(len(overlay.SOURCE_KEYS), 42)
        self.assertEqual(
            overlay.SOURCE_PATHS["p318_endpoint_transition"],
            overlay.PREFIX / "s22plus_fyg8_p318_cdc_acm_endpoint_transition.py",
        )
        receipts = overlay.source_receipts(ROOT)
        self.assertEqual(set(receipts), overlay.SOURCE_KEYS)
        self.assertEqual(
            receipts["p318_endpoint_transition"]["sha256"],
            hashlib.sha256(
                (ROOT / overlay.SOURCE_PATHS["p318_endpoint_transition"])
                .read_bytes()
            ).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
