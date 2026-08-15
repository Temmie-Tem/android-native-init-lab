import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "a90_h24_wlan_dependency_surface_inventory_v1.py"
)
INVENTORY = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "inventory/a90-h24-wlan-dependency-surface-inventory-v1.json"
)


def load_generator():
    spec = importlib.util.spec_from_file_location("a90_wp2_3_inventory", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load WP2-3 inventory generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A90H24WlanDependencySurfaceInventoryV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_generator()
        cls.data = json.loads(INVENTORY.read_text())

    def role(self, name):
        return next(record for record in self.data["roles"] if record["role"] == name)

    def test_generated_inventory_is_canonical_current_and_valid(self) -> None:
        self.assertEqual(INVENTORY.read_text(), self.module.canonical_text())
        self.assertEqual(self.module.validate_inventory(self.data), [])
        self.assertEqual(len(self.data["sourcePins"]), 12)
        for pin in self.data["sourcePins"]:
            raw = (ROOT / pin["path"]).read_bytes()
            self.assertEqual(len(raw), pin["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), pin["sha256"])

    def test_wp2_3_is_h0_only_and_retires_no_gate(self) -> None:
        authority = self.data["authority"]
        self.assertEqual(authority["tier"], "H0")
        for key, value in authority.items():
            if key != "tier":
                self.assertIs(value, False, key)
        status = self.data["status"]
        self.assertEqual(
            status["wp2_3"],
            "COMPLETE_H0_REQUIREMENT_AND_EVIDENCE_STATE_INVENTORY_ONLY",
        )
        self.assertEqual(
            status["dependencyClosure"],
            "BLOCKED_UNPROVED_H0D01_THROUGH_H0D10",
        )
        self.assertEqual(status["currentH24ExactOpaqueElfBindings"], 0)
        self.assertEqual(status["dependencyGatesRetired"], [])
        self.assertEqual(status["futureByteDerivedConsumer"], "ABSENT")
        self.assertEqual(status["executionImplementation"], "ABSENT")
        self.assertEqual(status["optionC"], "BLOCKED_RESEARCH_ONLY")

    def test_all_roles_and_all_dependency_slots_are_explicit(self) -> None:
        counts = self.data["counts"]
        self.assertEqual(counts["roleRecords"], 14)
        self.assertEqual(counts["sourceSelectedProcessInstances"], 16)
        self.assertEqual(counts["opaqueExternalElfRoles"], 11)
        self.assertEqual(counts["inProcessHelperBodies"], 2)
        self.assertEqual(counts["topologyOwnerElfs"], 1)
        self.assertEqual(counts["dependencySurfaceSlots"], 140)
        self.assertEqual(
            [record["role"] for record in self.data["roles"]],
            list(self.module.EXPECTED_ROLE_ORDER),
        )
        for record in self.data["roles"]:
            self.assertEqual(
                set(record["dependencySurfaces"]),
                set(self.module.SURFACE_KEYS),
            )
            self.assertEqual(record["allGateSlotsPresent"], list(self.module.GATE_IDS))
            self.assertFalse(record["dependencyClosureComplete"])
            self.assertFalse(record["executionEligible"])

    def test_selected_launch_is_exact_but_current_elf_binding_is_empty(self) -> None:
        selected_instance_count = 0
        for record in self.data["roles"]:
            instances = record["sourceSelectedInstances"]
            selected_instance_count += len(instances)
            self.assertEqual(
                [item["instanceId"] for item in instances], record["instanceIds"]
            )
            for launch in instances:
                self.assertTrue(launch["executable"])
                self.assertIsInstance(launch["argv"], list)
                self.assertTrue(launch["launchPredicate"])
                self.assertIn("identity", launch)
                self.assertIn("lifetime", launch)
                self.assertIn("cleanup", launch)
            binding = record["dependencySurfaces"]["artifact"]["currentH24ExactBinding"]
            self.assertEqual(binding["path"], instances[0]["executable"])
            for key in (
                "bytes",
                "sha256",
                "elfClass",
                "interpreter",
                "dtNeeded",
                "recursiveLibraryClosure",
            ):
                self.assertIsNone(binding[key], (record["role"], key))
        self.assertEqual(selected_instance_count, 16)

    def test_historical_cnss_facts_are_not_current_h24_bindings(self) -> None:
        cnss = self.role("cnss_daemon")
        artifact_facts = cnss["dependencySurfaces"]["artifact"]["facts"]
        self.assertEqual(len(artifact_facts), 1)
        historical = artifact_facts[0]
        self.assertEqual(
            historical["state"],
            "HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED",
        )
        self.assertEqual(
            historical["h24Applicability"],
            "UNPROVED_NOT_CURRENT_H24_BINDING",
        )
        self.assertEqual(historical["value"]["bytes"], 95112)
        self.assertEqual(
            historical["value"]["sha256"],
            "bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc",
        )
        self.assertIsNone(
            cnss["dependencySurfaces"]["artifact"]["currentH24ExactBinding"]["sha256"]
        )
        self.assertEqual(
            cnss["dependencySurfaces"]["property"]["facts"][0]["value"]["keys"],
            [
                "persist.vendor.cnss-daemon.debug_level",
                "persist.vendor.cnss-daemon.kmsg_logging",
            ],
        )

    def test_rfs_identity_conflicts_are_preserved_not_resolved_by_preference(self) -> None:
        rmt = self.role("rmt_storage")["identityContract"]
        tftp = self.role("tftp_server")["identityContract"]
        self.assertEqual(rmt["currentSelectedSourceIdentity"]["uid"], 0)
        self.assertEqual(tftp["currentSelectedSourceIdentity"]["uid"], 0)
        self.assertEqual(rmt["historicalConflicts"][0]["value"]["uid"], 9999)
        self.assertEqual(tftp["historicalConflicts"][0]["value"]["uid"], 2903)
        for contract in (rmt, tftp):
            self.assertFalse(contract["currentRuntimeAppliedIdentityProved"])
            self.assertFalse(contract["optionCExactIdentityEnvelopeProved"])
            self.assertEqual(
                contract["historicalConflicts"][0]["state"],
                "IDENTITY_CONFLICT_H24_RESOLUTION_REQUIRED",
            )

    def test_selected_property_modem_and_binder_surfaces_remain_bounded(self) -> None:
        shim = self.role("property-service-shim")
        shim_fact = shim["dependencySurfaces"]["property"]["facts"][0]
        self.assertEqual(shim_fact["value"]["path"], "/dev/socket/property_service")
        self.assertFalse(shim_fact["value"]["provesReadSeed"])
        holder = self.role("modem-holder")
        self.assertEqual(
            holder["dependencySurfaces"]["deviceKernel"]["facts"][0]["value"],
            {"path": "/dev/subsys_modem", "access": "open-and-hold"},
        )
        helper = self.role("wifi-helper")
        sd_fact = helper["dependencySurfaces"]["sdFreeProvenance"]["facts"][0]
        self.assertEqual(
            sd_fact["value"]["path"],
            "/mnt/sdext/a90/private-property-v317/v726/dev/__properties__",
        )
        self.assertFalse(sd_fact["value"]["successorAdmissible"])
        for role in ("servicemanager", "hwservicemanager", "vndservicemanager"):
            fact = self.role(role)["dependencySurfaces"]["binder"]["facts"][0]
            self.assertEqual(
                fact["value"]["endpointClass"],
                "NATIVE_GLOBAL_REJECTED_BY_WP2_2",
            )

    def test_design_projection_is_cross_bound_without_omitting_global_slots(self) -> None:
        design = json.loads(
            (
                ROOT
                / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
                "design/a90-h24-wlan-one-factor-ablation-design-v1.json"
            ).read_text()
        )
        expected = {
            unit["removedRole"]: unit["roleSpecificRelevantGateIds"]
            for unit in design["ablationUnits"]
        }
        for record in self.data["roles"]:
            if record["role"] == "wifi-helper":
                self.assertEqual(
                    record["designRoleSpecificGateIds"], list(self.module.GATE_IDS)
                )
            else:
                self.assertEqual(
                    record["designRoleSpecificGateIds"], expected[record["role"]]
                )
            self.assertEqual(record["allGateSlotsPresent"], list(self.module.GATE_IDS))

    def test_gate_coverage_is_total_and_all_unproved(self) -> None:
        self.assertEqual(
            [row["gateId"] for row in self.data["gateCoverage"]],
            list(self.module.GATE_IDS),
        )
        for row in self.data["gateCoverage"]:
            self.assertEqual(row["rolesWithExplicitSlot"], list(self.module.EXPECTED_ROLE_ORDER))
            self.assertEqual(row["status"], "UNPROVED")
            self.assertFalse(row["retirementCreditGranted"])

    def test_missing_inputs_and_next_sequence_do_not_smuggle_authority(self) -> None:
        plan = self.data["missingInputPlan"]
        self.assertEqual(plan["acquisitionAuthority"], "ABSENT_THIS_H0_UNIT")
        self.assertIn("current exact regular opaque ELF bytes", plan["offline"][0])
        self.assertIn("property reads/writes", plan["runtime"][0])
        sequence = self.data["nextSequencingConstraint"]
        self.assertIn("H0D10 bootstrap", sequence["beforeAnyExecution"])
        self.assertIn("H0D01 through H0D10", sequence["beforeOptionC"])
        self.assertIn("H0_ONLY", sequence["wp2_4"])

    def test_ten_negative_mutations_fail_closed(self) -> None:
        cases = []

        value = copy.deepcopy(self.data)
        value["roles"].pop()
        cases.append(("N01", value, "ROLE_SET_MISMATCH"))

        value = copy.deepcopy(self.data)
        value["roles"].append(copy.deepcopy(value["roles"][0]))
        cases.append(("N02", value, "ROLE_SET_MISMATCH"))

        value = copy.deepcopy(self.data)
        del value["roles"][0]["dependencySurfaces"]["binder"]
        cases.append(("N03", value, "SURFACE_SET_MISMATCH"))

        value = copy.deepcopy(self.data)
        value["roles"][0]["dependencySurfaces"]["artifact"]["currentH24ExactBinding"]["sha256"] = "0" * 64
        cases.append(("N04", value, "CURRENT_H24_ARTIFACT_BINDING_FORBIDDEN"))

        value = copy.deepcopy(self.data)
        value["status"]["dependencyGatesRetired"] = ["H0D01"]
        cases.append(("N05", value, "GATE_RETIREMENT_FORBIDDEN"))

        value = copy.deepcopy(self.data)
        value["authority"]["liveExecutionAuthorized"] = True
        cases.append(("N06", value, "AUTHORITY_MISMATCH"))

        value = copy.deepcopy(self.data)
        self._role_in(value, "rmt_storage")["identityContract"]["historicalConflicts"] = []
        cases.append(("N07", value, "IDENTITY_CONFLICT_MISSING"))

        value = copy.deepcopy(self.data)
        value["roles"][0]["dependencyClosureComplete"] = True
        cases.append(("N08", value, "DEPENDENCY_COMPLETION_FORBIDDEN"))

        value = copy.deepcopy(self.data)
        self._role_in(value, "cnss_daemon")["dependencySurfaces"]["artifact"]["facts"][0]["state"] = "CURRENT_H24_PROVED"
        cases.append(("N09", value, "FACT_STATE_MISMATCH"))

        value = copy.deepcopy(self.data)
        value["unexpectedAuthority"] = True
        cases.append(("N10", value, "TOP_LEVEL_SCHEMA_MISMATCH"))

        self.assertEqual(len(self.data["negativeCorpus"]), len(cases))
        for case_id, value, expected in cases:
            with self.subTest(case_id=case_id):
                self.assertIn(expected, self.module.validate_inventory(value))
                declared = next(
                    item for item in self.data["negativeCorpus"] if item["caseId"] == case_id
                )
                self.assertEqual(declared["expected"], expected)

    def test_pinned_semantic_model_rejects_source_derived_drift(self) -> None:
        mutations = []

        value = copy.deepcopy(self.data)
        self._role_in(value, "servicemanager")["sourceSelectedInstances"][0][
            "launchPredicate"
        ] = "forged-predicate"
        mutations.append(("launch-predicate", value))

        value = copy.deepcopy(self.data)
        self._role_in(value, "servicemanager")["sourceSelectedInstances"][0][
            "identity"
        ]["uid"] = 0
        mutations.append(("selected-identity", value))

        value = copy.deepcopy(self.data)
        self._role_in(value, "property-service-shim")["dependencySurfaces"][
            "property"
        ]["facts"][0]["value"]["provesReadSeed"] = True
        mutations.append(("property-proof-promotion", value))

        value = copy.deepcopy(self.data)
        self._role_in(value, "property-service-shim")["dependencySurfaces"][
            "property"
        ]["facts"] = []
        mutations.append(("selected-fact-removal", value))

        value = copy.deepcopy(self.data)
        self._role_in(value, "rmt_storage")["identityContract"][
            "historicalConflicts"
        ][0]["value"]["uid"] = 0
        mutations.append(("historical-conflict", value))

        value = copy.deepcopy(self.data)
        self._role_in(value, "servicemanager")["designRoleSpecificGateIds"] = []
        mutations.append(("design-gate-projection", value))

        for field, forged in (
            ("futureByteDerivedConsumer", "PRESENT"),
            ("executionImplementation", "READY"),
            ("optionC", "READY"),
        ):
            value = copy.deepcopy(self.data)
            value["status"][field] = forged
            mutations.append((f"status-{field}", value))

        for mutation, value in mutations:
            with self.subTest(mutation=mutation):
                self.assertIn(
                    "PINNED_SEMANTIC_MISMATCH",
                    self.module.validate_inventory(value),
                )

    @staticmethod
    def _role_in(value, role):
        return next(record for record in value["roles"] if record["role"] == role)


if __name__ == "__main__":
    unittest.main()
