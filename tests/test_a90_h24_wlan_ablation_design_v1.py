import copy
import hashlib
import importlib.util
import itertools
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT
    / "workspace/public/src/scripts/revalidation/a90_h24_wlan_ablation_design_v1.py"
)
DESIGN = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
    / "design/a90-h24-wlan-one-factor-ablation-design-v1.json"
)
PARENT = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
    / "inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json"
)


def load_generator():
    spec = importlib.util.spec_from_file_location("a90_h24_wlan_ablation_design", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load WP-H0-2 design generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A90H24WlanAblationDesignV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()
        cls.text = DESIGN.read_text()
        cls.data = json.loads(cls.text)
        cls.parent = json.loads(PARENT.read_text())

    def test_design_is_canonical_and_parent_pin_is_exact(self) -> None:
        self.assertEqual(self.text, self.generator.canonical_text())
        subprocess.run(
            [sys.executable, str(GENERATOR), "--check", str(DESIGN)],
            cwd=ROOT,
            check=True,
        )
        self.assertEqual(self.text, json.dumps(self.data, indent=2, sort_keys=True) + "\n")
        raw = PARENT.read_bytes()
        pin = self.data["parentInventory"]
        self.assertEqual(pin["path"], self.generator.PARENT_REL)
        self.assertEqual(pin["bytes"], len(raw))
        self.assertEqual(pin["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(pin["schema"], self.generator.PARENT_SCHEMA)

    def test_h0_design_grants_no_authority_or_live_transition(self) -> None:
        authority = self.data["authority"]
        self.assertEqual(authority["tier"], "H0")
        for key, value in authority.items():
            if key == "tier":
                continue
            self.assertIs(value, False, key)
        status = self.data["status"]
        self.assertEqual(status["currentState"], "H0_DESIGN_ONLY")
        self.assertEqual(status["wpH02Design"], "COMPLETE_H0_DESIGN_ONLY")
        self.assertEqual(status["correctedHealthyBaseline"], "ABSENT_UNPROVED")
        self.assertEqual(status["executionQualification"], "ABSENT")
        self.assertEqual(status["independentExecutionReview"], "ABSENT")
        self.assertEqual(self.data["stateMachine"]["currentReachableTransitions"], [])
        self.assertNotIn("workspace/private", self.text)

    def test_h24_is_rejected_as_a_baseline_and_placement_is_not_guessed(self) -> None:
        baseline = self.data["baselineFormation"]
        self.assertIs(baseline["h24IsHealthyAblationBaseline"], False)
        self.assertEqual(len(baseline["mandatoryCorrectionsBeforeAnyBaseline"]), 3)
        corrections = {
            item["correctionId"] for item in baseline["mandatoryCorrectionsBeforeAnyBaseline"]
        }
        self.assertEqual(
            corrections,
            {
                "A1_DEDUPLICATE_SM_HSM",
                "A2_ZERO_GLOBAL_SELINUX_MUTATION",
                "A3_BOUND_OBSERVER_AND_SD_FREE_BOOTSTRAP",
            },
        )
        self.assertTrue(
            all(
                item["necessityEvidence"] is False
                for item in baseline["mandatoryCorrectionsBeforeAnyBaseline"]
            )
        )
        baseline_gates = {
            item["gateId"]: item for item in baseline["dependencyGateProjection"]
        }
        self.assertEqual(set(baseline_gates), {f"H0D{i:02d}" for i in range(1, 11)})
        self.assertEqual(
            baseline_gates["H0D01"]["preExecutionAction"],
            "RETIRE_COMPLETE_RETAINED_SET_CLOSURE_BEFORE_EXECUTION",
        )
        self.assertEqual(
            baseline_gates["H0D04"]["preExecutionAction"],
            "NO_RETIREMENT_PRECONDITION_OBSERVER_MUST_BE_BOUND",
        )
        variants = baseline["serviceManagerPlacementVariants"]
        self.assertEqual(
            {item["variantId"] for item in variants},
            {"B0_EARLY_PAIR", "B0_PROVIDER_ADJACENT_PAIR"},
        )
        self.assertTrue(all(item["status"].startswith("UNPROVED") for item in variants))
        self.assertIn("mutually exclusive", baseline["variantRule"])
        self.assertIn("NO_GO_ABLATION_BASELINE", baseline["failureRule"])
        aggregate = baseline["aggregateDecisionModel"]
        self.assertEqual(
            aggregate["requiredVariantIds"],
            ["B0_EARLY_PAIR", "B0_PROVIDER_ADJACENT_PAIR"],
        )
        rows = aggregate["decisionTable"]
        states = {
            "NOT_RUN",
            "BASELINE_ADMITTED_G0",
            "BASELINE_REJECTED",
            "BASELINE_NON_ADMITTING",
        }
        pairs = {
            (
                row["variantResults"]["B0_EARLY_PAIR"],
                row["variantResults"]["B0_PROVIDER_ADJACENT_PAIR"],
            )
            for row in rows
        }
        self.assertEqual(len(rows), 16)
        self.assertEqual(pairs, set(itertools.product(states, repeat=2)))
        all_decisions = [
            (row, decision)
            for row in rows
            for decision in row["attemptOrderDecisions"]
        ]
        self.assertEqual(len(all_decisions), 25)
        for row in rows:
            present_ids = [
                variant_id
                for variant_id in aggregate["requiredVariantIds"]
                if row["variantResults"][variant_id] != "NOT_RUN"
            ]
            expected_orders = (
                {tuple(present_ids)}
                if len(present_ids) < 2
                else set(itertools.permutations(present_ids))
            )
            self.assertEqual(
                {
                    tuple(decision["attemptOrder"])
                    for decision in row["attemptOrderDecisions"]
                },
                expected_orders,
            )
            if "NOT_RUN" in row["variantResults"].values() or (
                "BASELINE_NON_ADMITTING" in row["variantResults"].values()
            ):
                self.assertTrue(
                    all(
                        decision["aggregateOutcome"]
                        != "NO_GO_ABLATION_BASELINE"
                        for decision in row["attemptOrderDecisions"]
                    )
                )
        no_go_pairs = [
            row
            for row in rows
            if any(
                decision["aggregateOutcome"] == "NO_GO_ABLATION_BASELINE"
                for decision in row["attemptOrderDecisions"]
            )
        ]
        self.assertEqual(len(no_go_pairs), 1)
        self.assertEqual(
            set(no_go_pairs[0]["variantResults"].values()),
            {"BASELINE_REJECTED"},
        )
        self.assertEqual(
            {
                decision["aggregateOutcome"]
                for decision in no_go_pairs[0]["attemptOrderDecisions"]
            },
            {"NO_GO_ABLATION_BASELINE"},
        )
        ordered_non_admitting = next(
            row
            for row in rows
            if row["variantResults"]
            == {
                "B0_EARLY_PAIR": "BASELINE_NON_ADMITTING",
                "B0_PROVIDER_ADJACENT_PAIR": "BASELINE_REJECTED",
            }
        )
        by_order = {
            tuple(decision["attemptOrder"]): decision["aggregateOutcome"]
            for decision in ordered_non_admitting["attemptOrderDecisions"]
        }
        self.assertEqual(
            by_order[("B0_PROVIDER_ADJACENT_PAIR", "B0_EARLY_PAIR")],
            "BASELINE_AGGREGATE_PENDING_NO_SELECTION",
        )
        self.assertEqual(
            by_order[("B0_EARLY_PAIR", "B0_PROVIDER_ADJACENT_PAIR")],
            "INVALID_EFFECT_AFTER_NON_ADMITTING_RESULT_NO_SELECTION",
        )
        both_non_admitting = next(
            row
            for row in rows
            if set(row["variantResults"].values()) == {"BASELINE_NON_ADMITTING"}
        )
        self.assertTrue(
            all(
                decision["aggregateOutcome"]
                == "INVALID_EFFECT_AFTER_NON_ADMITTING_RESULT_NO_SELECTION"
                for decision in both_non_admitting["attemptOrderDecisions"]
            )
        )
        self.assertIn("Duplicate ID", aggregate["inputRule"])
        self.assertIn("both distinct required variant IDs", aggregate["noGoRule"])
        safety_gate = {
            item["rejectedVariantDeviceSafetyState"]: item
            for item in aggregate["rejectedVariantSafetyGate"]
        }
        self.assertEqual(
            set(safety_gate),
            {"BASELINE_HEALTHY", "RESIDENT_HEALTHY", "RECOVERY_REQUIRED"},
        )
        self.assertIs(
            safety_gate["BASELINE_HEALTHY"][
                "freshOtherVariantQualificationMayBegin"
            ],
            False,
        )
        self.assertIs(
            safety_gate["RECOVERY_REQUIRED"][
                "freshOtherVariantQualificationMayBegin"
            ],
            False,
        )
        self.assertEqual(
            safety_gate["RECOVERY_REQUIRED"]["gateOutcome"], "RECOVERY_PARKED"
        )
        self.assertIs(
            safety_gate["RESIDENT_HEALTHY"][
                "freshOtherVariantQualificationMayBegin"
            ],
            True,
        )
        self.assertIn("fresh qualification", safety_gate["RESIDENT_HEALTHY"]["reason"])
        self.assertIn("grants no UNIT_PREPARED", aggregate["freshOtherVariantRule"])

    def test_every_parent_role_has_a_scoped_unproved_necessity_argument(self) -> None:
        parent_roles = {item["role"] for item in self.parent["components"]}
        arguments = self.data["necessityArguments"]
        self.assertEqual({item["role"] for item in arguments}, parent_roles)
        self.assertEqual(len(arguments), 14)
        self.assertTrue(
            all(item["currentConclusion"] == "INDIVIDUAL_NECESSITY_UNPROVED" for item in arguments)
        )
        for item in arguments:
            self.assertTrue(item["sourceInstances"])
            self.assertTrue(item["sourceExecutables"])
            self.assertTrue(item["sourceAnchors"])
            self.assertTrue(item["dependencyGateIds"])
            self.assertEqual(item["conclusionScope"], "FROZEN_H24_SELECTED_SOURCE_GRAPH_ONLY")
        by_role = {item["role"]: item for item in arguments}
        self.assertIsNone(by_role["wifi-helper"]["ablationStage"])
        self.assertIn("not a component-removal variable", by_role["wifi-helper"]["staticHypothesis"])
        self.assertIn("not renamed to rmtfs", by_role["rmt_storage"]["staticHypothesis"])

    def test_thirteen_units_each_remove_exactly_one_non_owner_role(self) -> None:
        units = self.data["ablationUnits"]
        self.assertEqual(len(units), 13)
        self.assertEqual([item["order"] for item in units], list(range(1, 14)))
        parent_roles = {item["role"] for item in self.parent["components"]}
        self.assertEqual(
            {item["removedRole"] for item in units},
            parent_roles - {"wifi-helper"},
        )
        for unit in units:
            self.assertEqual(unit["deltaCardinality"], 1)
            self.assertEqual(unit["parentGeneration"], "EXACT_HEALTHY_G_N")
            self.assertEqual(unit["effect"], "DISABLE_EXACTLY_ONE_ROLE_AT_CONSTRUCTION")
            self.assertEqual(unit["replayPolicy"], "NEVER_REDISPATCH_AFTER_DURABLE_EFFECT_INTENT")
            self.assertEqual(unit["failureChaining"], "FORBIDDEN")
            self.assertIs(unit["globalNecessityClaimAllowed"], False)
            projections = {
                item["gateId"]: item for item in unit["dependencyGateProjection"]
            }
            self.assertIn("H0D01", projections)
            self.assertIn("H0D10", projections)
            self.assertEqual(
                projections["H0D01"]["preExecutionAction"],
                "RETIRE_COMPLETE_RETAINED_SET_CLOSURE_BEFORE_EXECUTION",
            )
            self.assertEqual(
                projections["H0D10"]["preExecutionAction"],
                "PROVE_SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_BEFORE_EXECUTION",
            )
            for projection in projections.values():
                if projection["parentPreExecutionRequirement"] == (
                    "BOUNDED_EXECUTION_PRODUCES_RETIREMENT_EVIDENCE_NOT_A_PRECONDITION"
                ):
                    self.assertEqual(
                        projection["preExecutionAction"],
                        "NO_RETIREMENT_PRECONDITION_OBSERVER_MUST_BE_BOUND",
                    )
                    self.assertEqual(
                        projection["executionEvidenceRole"],
                        "EXECUTION_PRODUCES_RETIREMENT_EVIDENCE",
                    )
            self.assertTrue(unit["roleSpecificRelevantGateIds"])

    def test_generation_promotion_never_chains_failure_or_batch(self) -> None:
        model = self.data["generationModel"]
        self.assertIn("not h24", model["initialGeneration"].replace("_", " ").lower())
        self.assertIn("changes exactly one role", model["unitRule"])
        self.assertIn("non-promotable", model["failedUnitRule"])
        self.assertIn("never chain", model["failedUnitRule"])
        self.assertIn("fresh full baseline qualification", model["promotionRule"])
        self.assertIn("Never promote a multi-removal batch", model["interactionRule"])
        terminals = self.data["outcomeVocabulary"]
        self.assertEqual(
            set(terminals),
            {
                "deviceSafetyState",
                "experimentProof",
                "workflowState",
                "generationOutcome",
            },
        )
        self.assertEqual(
            set(terminals["deviceSafetyState"]),
            {"BASELINE_HEALTHY", "RESIDENT_HEALTHY", "RECOVERY_REQUIRED"},
        )
        self.assertEqual(
            set(terminals["experimentProof"]),
            {"PROVED", "REFUTED", "NO_PROOF_OBSERVER"},
        )
        self.assertIn(
            "generation only",
            terminals["generationOutcome"]["REMOVAL_SUPPORTED_FOR_GENERATION"],
        )
        self.assertIn(
            "generation only",
            terminals["generationOutcome"]["REMOVAL_REFUTED_FOR_GENERATION"],
        )

    def test_sd_free_bootstrap_precedes_execution_and_final_seed_follows_ablation(self) -> None:
        bootstrap = self.data["sdFreeBootstrap"]
        self.assertEqual(
            bootstrap["selectedRule"],
            "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET_OR_NO_GO",
        )
        joined = " ".join(bootstrap["beforeAnyExecution"])
        self.assertIn("Never read, copy, relocate, or bless the private whole property snapshot", joined)
        self.assertIn("baseline formation is NO_GO", joined)
        self.assertIn("separate design", bootstrap["notSelectedAlternative"])
        self.assertEqual(
            bootstrap["afterAblation"]["acceptedTerminals"],
            ["PROPERTY_ABSENT_PROVED", "PROPERTY_FINITE_SEED_PROVED"],
        )
        parent_h0d10 = self.parent["dependencyGates"][-1]
        self.assertEqual(
            parent_h0d10["preExecutionHalf"]["requiredTerminal"],
            "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED",
        )
        self.assertEqual(len(self.data["propertyExperiments"]), 2)
        self.assertEqual(
            {item["acceptedSuccess"] for item in self.data["propertyExperiments"]},
            {"PROPERTY_ABSENT_PROVED", "PROPERTY_FINITE_SEED_PROVED"},
        )

    def test_result_contract_separates_observer_failure_and_uses_measured_budgets(self) -> None:
        status = self.data["status"]
        self.assertEqual(
            status["budgetStatus"],
            "UNSET_REQUIRES_MEASURED_HEALTHY_BASELINE",
        )
        result = self.data["resultContract"]
        self.assertIn("No numeric pass budget exists", result["budgetRule"])
        self.assertIn("experiment proof", result["noProofRule"])
        self.assertIn("device safety", result["noProofRule"])
        self.assertIn("contradiction has proof precedence", result["noProofRule"])
        model = result["classificationModel"]
        self.assertEqual(
            set(model["requiredRawFields"]),
            {
                "proofSubject",
                "observerOutcome",
                "experimentEvidence",
                "attribution",
                "safetyClosureEvidence",
            },
        )
        proof_rows = model["proofDecisionTable"]
        expected_proof_keys = set(
            itertools.product(
                ("VALID_COMPLETE", "INVALID_OR_UNRESOLVED"),
                (
                    "ALL_REQUIRED_PASSED",
                    "ATTRIBUTABLE_CONTRADICTION",
                    "NOT_OBSERVED_OR_AMBIGUOUS",
                ),
                ("MATCHES_PROOF_SUBJECT", "DOES_NOT_MATCH_OR_UNRESOLVED"),
            )
        )
        actual_proof_keys = {
            (
                item["observerClass"],
                item["experimentEvidenceClass"],
                item["attributionRelation"],
            )
            for item in proof_rows
        }
        self.assertEqual(len(proof_rows), 12)
        self.assertEqual(actual_proof_keys, expected_proof_keys)
        contradiction_with_observer_fault = next(
            item
            for item in proof_rows
            if item["observerClass"] == "INVALID_OR_UNRESOLVED"
            and item["experimentEvidenceClass"] == "ATTRIBUTABLE_CONTRADICTION"
            and item["attributionRelation"] == "MATCHES_PROOF_SUBJECT"
        )
        self.assertEqual(
            contradiction_with_observer_fault["experimentProof"], "REFUTED"
        )
        self.assertEqual(len(model["safetyDecisionTable"]), 3)
        safety = {
            item["deviceSafetyState"]: item["workflowState"]
            for item in model["safetyDecisionTable"]
        }
        self.assertEqual(safety["RECOVERY_REQUIRED"], "RECOVERY_PARKED")
        generation_rows = model["generationDecisionTable"]
        expected_generation_keys = set(
            itertools.product(
                ("BASELINE", "ROLE_REMOVAL"),
                ("PROVED", "REFUTED", "NO_PROOF_OBSERVER"),
                ("BASELINE_HEALTHY", "RESIDENT_HEALTHY", "RECOVERY_REQUIRED"),
            )
        )
        actual_generation_keys = {
            (
                item["proofSubject"],
                item["experimentProof"],
                item["deviceSafetyState"],
            )
            for item in generation_rows
        }
        self.assertEqual(len(generation_rows), 18)
        self.assertEqual(actual_generation_keys, expected_generation_keys)
        g0_admitting = [item for item in generation_rows if item["g0AdmissionEligible"]]
        self.assertEqual(len(g0_admitting), 1)
        self.assertEqual(
            (
                g0_admitting[0]["proofSubject"],
                g0_admitting[0]["experimentProof"],
                g0_admitting[0]["deviceSafetyState"],
                g0_admitting[0]["generationOutcome"],
            ),
            ("BASELINE", "PROVED", "RESIDENT_HEALTHY", "BASELINE_ADMITTED_G0"),
        )
        baseline_final_health_pending = next(
            item
            for item in generation_rows
            if item["proofSubject"] == "BASELINE"
            and item["experimentProof"] == "PROVED"
            and item["deviceSafetyState"] == "BASELINE_HEALTHY"
        )
        self.assertIs(baseline_final_health_pending["g0AdmissionEligible"], False)
        self.assertEqual(
            baseline_final_health_pending["generationOutcome"],
            "BASELINE_PROVED_FINAL_HEALTH_PENDING_NO_ADMISSION",
        )
        promotable = [item for item in generation_rows if item["promotionEligible"]]
        self.assertEqual(len(promotable), 1)
        self.assertEqual(
            (
                promotable[0]["proofSubject"],
                promotable[0]["experimentProof"],
                promotable[0]["deviceSafetyState"],
            ),
            ("ROLE_REMOVAL", "PROVED", "RESIDENT_HEALTHY"),
        )
        refuted_and_parked = next(
            item
            for item in generation_rows
            if item["proofSubject"] == "ROLE_REMOVAL"
            and item["experimentProof"] == "REFUTED"
            and item["deviceSafetyState"] == "RECOVERY_REQUIRED"
        )
        self.assertEqual(
            refuted_and_parked["generationOutcome"],
            "REMOVAL_REFUTED_FOR_GENERATION",
        )
        self.assertIn("may coexist", model["coexistenceRule"])
        self.assertIn("Unknown enum", model["invalidInputRule"])
        self.assertEqual(
            set(result["metrics"]),
            {"latency", "footprint", "runtime", "network", "dependency", "cleanup"},
        )
        for metric_set in result["metrics"].values():
            self.assertTrue(metric_set)
        self.assertIn("wmi-ready", result["functionalProof"])
        self.assertIn("dhcp-and-route", result["functionalProof"])

    def test_parent_mutations_fail_closed(self) -> None:
        removed = copy.deepcopy(self.parent)
        removed["components"].pop()
        with self.assertRaises(ValueError):
            self.generator.build_design(removed)

        authority = copy.deepcopy(self.parent)
        authority["authority"]["d1Authorized"] = True
        with self.assertRaises(ValueError):
            self.generator.build_design(authority)

        retired = copy.deepcopy(self.parent)
        retired["dependencyGates"][0]["status"] = "PROVED"
        with self.assertRaises(ValueError):
            self.generator.build_design(retired)

        bootstrap = copy.deepcopy(self.parent)
        bootstrap["dependencyGates"][-1]["preExecutionHalf"]["requiredTerminal"] = "WEAK"
        with self.assertRaises(ValueError):
            self.generator.build_design(bootstrap)


if __name__ == "__main__":
    unittest.main()
