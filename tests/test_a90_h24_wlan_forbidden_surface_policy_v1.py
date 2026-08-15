import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "a90_h24_wlan_forbidden_surface_policy_v1.py"
)
POLICY = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/"
    "policy/a90-h24-wlan-forbidden-surface-policy-v1.json"
)


def load_generator():
    spec = importlib.util.spec_from_file_location("a90_wp2_2_policy", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load WP2-2 policy generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A90H24WlanForbiddenSurfacePolicyV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_generator()
        cls.data = json.loads(POLICY.read_text())
        cls.base = copy.deepcopy(cls.data["referenceVariants"][0]["declaration"])

    def validate(self, value):
        return self.module.validate_surface_contract(value)

    def refresh_graph_digest(self, value) -> None:
        graph = value["componentGraph"]
        digest = self.module._canonical_digest(graph["instances"])
        graph["manifestSha256"] = digest
        graph["consumerManifestSha256"] = {
            consumer: digest for consumer in self.module.CONSUMERS
        }

    def set_role_removal_lineage(
        self,
        value,
        *,
        parent_sha256,
        parent_instances,
        unit_id,
        removed_role,
        removed_instance_id,
    ) -> None:
        value["componentGraph"]["lineage"] = {
            "kind": "WP_H0_2_ONE_ROLE_REMOVAL",
            "parentManifestSha256": parent_sha256,
            "parentInstances": parent_instances,
            "ablationUnitId": unit_id,
            "removedRole": removed_role,
            "removedInstanceIds": [removed_instance_id],
        }

    def test_generated_policy_is_canonical_and_current(self) -> None:
        self.assertEqual(POLICY.read_text(), self.module.canonical_text())
        self.module._require_source_contract(self.module._load_inputs())
        self.assertEqual(len(self.data["sourcePins"]), 5)
        for pin in self.data["sourcePins"]:
            raw = (ROOT / pin["path"]).read_bytes()
            self.assertEqual(len(raw), pin["bytes"])
            self.assertEqual(
                __import__("hashlib").sha256(raw).hexdigest(),
                pin["sha256"],
            )

    def test_policy_is_h0_only_and_retires_no_gate(self) -> None:
        authority = self.data["authority"]
        self.assertEqual(authority["tier"], "H0")
        for key, value in authority.items():
            if key != "tier":
                self.assertIs(value, False, key)
        status = self.data["status"]
        self.assertEqual(
            status["wp2_2"],
            "COMPLETE_H0_STATIC_POLICY_AND_NEGATIVE_CORPUS_ONLY",
        )
        self.assertEqual(status["dependencyGatesRetired"], [])
        self.assertEqual(status["futureByteDerivationConsumer"], "ABSENT")
        self.assertEqual(status["executionImplementation"], "ABSENT")
        self.assertEqual(status["executionQualification"], "ABSENT")
        self.assertEqual(status["optionC"], "BLOCKED_RESEARCH_ONLY")

    def test_h24_static_rejection_is_not_mislabeled_live_evidence(self) -> None:
        disposition = self.data["currentH24SourceDisposition"]
        self.assertEqual(
            disposition["sourceReachableHazards"],
            [
                "DUPLICATE_SERVICEMANAGER_AND_HWSERVICEMANAGER_CONSTRUCTION",
                "GLOBAL_SELINUXFS_RW_BIND_POLICY_LOAD_AND_ENFORCE_WRITE",
                "NATIVE_GLOBAL_BINDER_CHARDEV_MATERIALIZATION_10_79_80_81",
                "SD_WHOLE_PROPERTY_SNAPSHOT_AND_ACCEPTED_CACHE_RELOCATION_CLASS",
            ],
        )
        self.assertIs(disposition["h24LiveExecutionOfSelectedRoute"], False)
        self.assertEqual(
            disposition["liveEffectClaim"],
            "UNPROVED_H24_D1_STOPPED_BEFORE_WIFI_HELPER_ROUTE",
        )
        self.assertIs(disposition["baselineAdmissible"], False)

    def test_both_deduplicated_reference_variants_pass_only_static_guards(self) -> None:
        variants = self.data["referenceVariants"]
        self.assertEqual(
            [item["variantId"] for item in variants],
            ["B0_EARLY_PAIR", "B0_PROVIDER_ADJACENT_PAIR"],
        )
        for item in variants:
            declaration = item["declaration"]
            roles = [
                component["role"]
                for component in declaration["componentGraph"]["instances"]
            ]
            self.assertEqual(len(roles), 14)
            self.assertEqual(roles.count("servicemanager"), 1)
            self.assertEqual(roles.count("hwservicemanager"), 1)
            result = self.validate(declaration)
            self.assertEqual(
                result["outcome"],
                "STATIC_REINTRODUCTION_GUARDS_PASS_H0_ONLY",
            )
            self.assertTrue(result["surfacePolicySatisfied"])
            self.assertFalse(result["candidateEligible"])
            self.assertFalse(result["executionEligible"])
            self.assertIn(
                "H0D10_PUBLIC_BOOTSTRAP_SUPERSET_UNPROVED",
                result["pendingProofs"],
            )
            self.assertIn(
                "FUTURE_BYTE_DERIVED_DECLARATION_CONSUMER_ABSENT",
                result["pendingProofs"],
            )

    def test_duplicate_manager_and_consumer_drift_are_rejected(self) -> None:
        for role, instance_id, code in (
            (
                "servicemanager",
                "servicemanager#reintroduced",
                "DUPLICATE_SERVICEMANAGER_FORBIDDEN",
            ),
            (
                "hwservicemanager",
                "hwservicemanager#reintroduced",
                "DUPLICATE_HWSERVICEMANAGER_FORBIDDEN",
            ),
        ):
            value = copy.deepcopy(self.base)
            value["componentGraph"]["instances"].append(
                {"instanceId": instance_id, "role": role}
            )
            self.refresh_graph_digest(value)
            result = self.validate(value)
            self.assertIn(code, result["findingCodes"])
            self.assertFalse(result["surfacePolicySatisfied"])

        value = copy.deepcopy(self.base)
        value["componentGraph"]["consumerManifestSha256"]["health"] = "f" * 64
        self.assertEqual(
            self.validate(value)["findingCodes"],
            ["COMPONENT_CONSUMER_DIGEST_DRIFT"],
        )

    def test_later_generation_may_remove_a_manager_but_never_duplicate_one(self) -> None:
        value = copy.deepcopy(self.base)
        parent_sha256 = value["componentGraph"]["manifestSha256"]
        parent_instances = copy.deepcopy(value["componentGraph"]["instances"])
        removed_instance_id = next(
            item["instanceId"]
            for item in value["componentGraph"]["instances"]
            if item["role"] == "servicemanager"
        )
        value["componentGraph"]["variantId"] = "G_N_ROLE_ABLATION"
        value["componentGraph"]["instances"] = [
            item
            for item in value["componentGraph"]["instances"]
            if item["role"] != "servicemanager"
        ]
        self.set_role_removal_lineage(
            value,
            parent_sha256=parent_sha256,
            parent_instances=parent_instances,
            unit_id="WP-H0-2-A5a",
            removed_role="servicemanager",
            removed_instance_id=removed_instance_id,
        )
        self.refresh_graph_digest(value)
        result = self.validate(value)
        self.assertTrue(result["surfacePolicySatisfied"])
        self.assertNotIn(
            "BASELINE_EXACT_ONE_SERVICEMANAGER_REQUIRED",
            result["findingCodes"],
        )
        self.assertFalse(result["executionEligible"])
        self.assertIn(
            "WP_H0_2_GENERATION_LINEAGE_CONSUMER_ABSENT",
            result["pendingProofs"],
        )

        multi = copy.deepcopy(value)
        multi["componentGraph"]["instances"] = [
            item
            for item in multi["componentGraph"]["instances"]
            if item["role"] != "tftp_server"
        ]
        self.refresh_graph_digest(multi)
        self.assertIn(
            "ROLE_REMOVAL_LINEAGE_MISMATCH",
            self.validate(multi)["findingCodes"],
        )

        value["componentGraph"]["instances"].append(
            {"instanceId": "servicemanager#restored", "role": "servicemanager"}
        )
        value["componentGraph"]["instances"].append(
            {"instanceId": "servicemanager#duplicate", "role": "servicemanager"}
        )
        self.refresh_graph_digest(value)
        self.assertIn(
            "DUPLICATE_SERVICEMANAGER_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

    def test_baseline_manager_placement_and_known_role_vocabulary_are_exact(self) -> None:
        value = copy.deepcopy(self.base)
        value["componentGraph"]["instances"] = [
            item
            for item in value["componentGraph"]["instances"]
            if item["role"] != "cnss_daemon"
        ]
        self.refresh_graph_digest(value)
        self.assertIn(
            "BASELINE_COMPONENT_GRAPH_MISMATCH",
            self.validate(value)["findingCodes"],
        )

        value = copy.deepcopy(self.base)
        manager = next(
            item
            for item in value["componentGraph"]["instances"]
            if item["role"] == "servicemanager"
        )
        manager["instanceId"] = "servicemanager#wrong-placement"
        self.refresh_graph_digest(value)
        self.assertIn(
            "BASELINE_MANAGER_PLACEMENT_IDENTITY_MISMATCH",
            self.validate(value)["findingCodes"],
        )

        value = copy.deepcopy(self.base)
        value["componentGraph"]["variantId"] = "G_N_ROLE_ABLATION"
        value["componentGraph"]["instances"].append(
            {"instanceId": "unreviewed-backend#1", "role": "unreviewed-backend"}
        )
        self.refresh_graph_digest(value)
        self.assertIn(
            "UNKNOWN_COMPONENT_ROLE_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

        value = copy.deepcopy(self.base)
        value["componentGraph"]["variantId"] = "G_N_ROLE_ABLATION"
        value["componentGraph"]["instances"].append(
            {"instanceId": "pd_mapper#duplicate", "role": "pd_mapper"}
        )
        self.refresh_graph_digest(value)
        self.assertIn(
            "DUPLICATE_COMPONENT_ROLE_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

    def test_nonbaseline_lineage_is_explicit_and_never_execution_authority(self) -> None:
        value = copy.deepcopy(self.base)
        value["componentGraph"]["variantId"] = "REDUCED_NATIVE_INTEGRATION"
        value["componentGraph"]["lineage"] = {
            "kind": "TOPOLOGY_INTEGRATION",
            "parentManifestSha256": value["componentGraph"]["manifestSha256"],
            "parentInstances": copy.deepcopy(value["componentGraph"]["instances"]),
            "ablationUnitId": None,
            "removedRole": None,
            "removedInstanceIds": [],
        }
        result = self.validate(value)
        self.assertTrue(result["surfacePolicySatisfied"])
        self.assertIn(
            "TOPOLOGY_INTEGRATION_LINEAGE_CONSUMER_ABSENT",
            result["pendingProofs"],
        )
        self.assertFalse(result["executionEligible"])

        value["componentGraph"]["lineage"]["removedRole"] = "cnss_daemon"
        self.assertIn(
            "TOPOLOGY_INTEGRATION_LINEAGE_MISMATCH",
            self.validate(value)["findingCodes"],
        )

    def test_each_global_selinux_mutation_form_is_rejected(self) -> None:
        operations = (
            {
                "kind": "BIND_MOUNT",
                "source": "/sys/fs/selinux",
                "target": "/run/a90-wlan-capsule/sys/fs/selinux",
                "access": "RW",
                "scope": "GLOBAL_KERNEL",
            },
            {
                "kind": "WRITE",
                "source": None,
                "target": "/sys/fs/selinux/load",
                "access": "WRITE",
                "scope": "GLOBAL_KERNEL",
            },
            {
                "kind": "WRITE",
                "source": None,
                "target": "/sys/fs/selinux/enforce",
                "access": "WRITE",
                "scope": "GLOBAL_KERNEL",
            },
        )
        for operation in operations:
            value = copy.deepcopy(self.base)
            value["selinuxSurface"]["operations"] = [operation]
            result = self.validate(value)
            self.assertEqual(
                result["findingCodes"],
                ["GLOBAL_SELINUX_MUTATION_FORBIDDEN"],
            )
            self.assertFalse(result["executionEligible"])

    def test_unknown_selinux_operation_vocabulary_fails_closed(self) -> None:
        for field, replacement in (("kind", "MMAP"), ("access", "EXEC"), ("scope", "UNKNOWN")):
            value = copy.deepcopy(self.base)
            operation = {
                "kind": "OPEN",
                "source": None,
                "target": "/run/a90-wlan-capsule/policy",
                "access": "READ",
                "scope": "CAPSULE_PRIVATE",
            }
            operation[field] = replacement
            value["selinuxSurface"]["operations"] = [operation]
            self.assertIn(
                "SELINUX_OPERATION_SCHEMA_MISMATCH",
                self.validate(value)["findingCodes"],
                field,
            )

        for operation in (
            {
                "kind": "WRITE",
                "source": None,
                "target": "/sys/fs/selinux/enforce",
                "access": "READ",
                "scope": "GLOBAL_KERNEL",
            },
            {
                "kind": "BIND_MOUNT",
                "source": None,
                "target": "/run/a90-wlan-capsule/sys/fs/selinux",
                "access": "READ",
                "scope": "CAPSULE_PRIVATE",
            },
        ):
            value = copy.deepcopy(self.base)
            value["selinuxSurface"]["operations"] = [operation]
            self.assertIn(
                "SELINUX_OPERATION_SCHEMA_MISMATCH",
                self.validate(value)["findingCodes"],
            )

    def test_global_binder_is_rejected_by_path_backing_and_rdev(self) -> None:
        endpoint = {
            "path": "/dev/binder",
            "backingClass": "NATIVE_GLOBAL_BINDER_CHARDEV",
            "major": 10,
            "minor": 81,
            "namespaceScope": "NATIVE_GLOBAL",
        }
        value = copy.deepcopy(self.base)
        value["binderSurface"] = {
            "endpointMode": "CAPSULE_PRIVATE_BINDERFS_PENDING_H0D05",
            "proofTerminal": "UNPROVED_H0D05",
            "proofBindingSha256": None,
            "endpoints": [endpoint],
        }
        findings = set(self.validate(value)["findingCodes"])
        self.assertTrue(
            {
                "GLOBAL_BINDER_PATH_FORBIDDEN",
                "GLOBAL_BINDER_BACKING_FORBIDDEN",
                "GLOBAL_BINDER_RDEV_FORBIDDEN",
                "GLOBAL_BINDER_NAMESPACE_FORBIDDEN",
            }.issubset(findings)
        )

        value["binderSurface"]["endpoints"][0].update(
            path="/run/a90-wlan-capsule/binderfs/binder",
            namespaceScope="CAPSULE_PRIVATE",
        )
        findings = set(self.validate(value)["findingCodes"])
        self.assertIn("GLOBAL_BINDER_BACKING_FORBIDDEN", findings)
        self.assertIn("GLOBAL_BINDER_RDEV_FORBIDDEN", findings)

    def test_private_binderfs_is_not_mistaken_for_proved_or_executable(self) -> None:
        example = next(
            item
            for item in self.data["conditionalPrivateSurfaceExamples"]
            if item["exampleId"] == "private-binderfs-still-unproved"
        )
        result = self.validate(example["declaration"])
        self.assertTrue(result["surfacePolicySatisfied"])
        self.assertEqual(result["findingCodes"], [])
        self.assertIn("H0D05_PRIVATE_BINDERFS_PROOF_REQUIRED", result["pendingProofs"])
        self.assertFalse(result["executionEligible"])

    def test_malformed_binder_endpoint_types_reject_without_parser_failure(self) -> None:
        example = next(
            item
            for item in self.data["conditionalPrivateSurfaceExamples"]
            if item["exampleId"] == "private-binderfs-still-unproved"
        )
        value = copy.deepcopy(example["declaration"])
        value["binderSurface"]["endpoints"][0]["path"] = ["not", "a", "path"]
        self.assertIn(
            "NONCANONICAL_PATH_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

        value = copy.deepcopy(example["declaration"])
        value["binderSurface"]["endpoints"][0]["major"] = True
        self.assertIn(
            "BINDER_ENDPOINT_SCHEMA_MISMATCH",
            self.validate(value)["findingCodes"],
        )

    def test_sd_and_snapshot_aliases_are_rejected_by_path_and_provenance(self) -> None:
        def finite(value, source):
            value["propertyInput"] = {
                "sourceClass": "PUBLIC_DETERMINISTIC_FINITE_SEED",
                "preExecutionTerminal": "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED",
                "finalTerminal": "PROPERTY_FINITE_SEED_PROVED",
                "wholeSnapshotAccepted": False,
                "privateSnapshotBytesUsed": False,
                "sources": [source],
            }

        value = copy.deepcopy(self.base)
        finite(
            value,
            {
                "path": "/mnt/sdext/a90/renamed-seed.json",
                "kind": "FINITE_PROPERTY_SEED",
                "provenance": "PUBLIC_DETERMINISTIC_GENERATOR",
                "originalSourceClass": "PUBLIC_SOURCE",
            },
        )
        self.assertIn(
            "SD_OR_LEGACY_SNAPSHOT_PATH_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

        value = copy.deepcopy(self.base)
        finite(
            value,
            {
                "path": "/cache/innocent-name/seed.json",
                "kind": "FINITE_PROPERTY_SEED",
                "provenance": "RELOCATED_PRIVATE_WHOLE_SNAPSHOT",
                "originalSourceClass": "PRIVATE_WHOLE_SNAPSHOT",
            },
        )
        self.assertIn(
            "PRIVATE_SNAPSHOT_PROVENANCE_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

        value = copy.deepcopy(self.base)
        finite(
            value,
            {
                "path": "/cache/a90-public/seed.json",
                "kind": "WHOLE_PROPERTY_SNAPSHOT",
                "provenance": "PUBLIC_DETERMINISTIC_GENERATOR",
                "originalSourceClass": "PUBLIC_SOURCE",
            },
        )
        self.assertIn(
            "WHOLE_PROPERTY_SNAPSHOT_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

    def test_private_property_service_remains_pending_not_proved(self) -> None:
        example = next(
            item
            for item in self.data["conditionalPrivateSurfaceExamples"]
            if item["exampleId"] == "private-property-service-still-unproved"
        )
        result = self.validate(example["declaration"])
        self.assertTrue(result["surfacePolicySatisfied"])
        self.assertIn(
            "H0D04_PRIVATE_PROPERTY_SERVICE_PROOF_REQUIRED",
            result["pendingProofs"],
        )
        self.assertFalse(result["executionEligible"])

        value = copy.deepcopy(example["declaration"])
        endpoint = value["propertyService"]["endpoints"][0]
        endpoint.update(
            path="/dev/socket/property_service",
            namespaceScope="NATIVE_GLOBAL",
            backingClass="INHERITED_NATIVE_FILESYSTEM_SOCKET",
            scmRights=True,
            inherited=True,
        )
        self.assertIn(
            "GLOBAL_OR_CAPABILITY_PROPERTY_ENDPOINT_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

        value = copy.deepcopy(example["declaration"])
        value["propertyService"]["endpoints"][0]["path"] = "/run/not-the-capsule/property_service"
        self.assertIn(
            "GLOBAL_OR_CAPABILITY_PROPERTY_ENDPOINT_FORBIDDEN",
            self.validate(value)["findingCodes"],
        )

    def test_public_bootstrap_superset_is_representable_but_h0d04_stays_pending(self) -> None:
        value = copy.deepcopy(self.base)
        value["propertyInput"] = {
            "sourceClass": "PUBLIC_DETERMINISTIC_BOOTSTRAP_SUPERSET",
            "preExecutionTerminal": "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED",
            "finalTerminal": "UNPROVED_H0D04_POST_ABLATION",
            "wholeSnapshotAccepted": False,
            "privateSnapshotBytesUsed": False,
            "sources": [
                {
                    "path": "/run/a90-wlan-bootstrap/property-input-v1.json",
                    "kind": "DETERMINISTIC_BOOTSTRAP_INPUT",
                    "provenance": "PUBLIC_DETERMINISTIC_GENERATOR",
                    "originalSourceClass": "PUBLIC_SOURCE",
                }
            ],
        }
        result = self.validate(value)
        self.assertTrue(result["surfacePolicySatisfied"])
        self.assertIn("H0D04_PROPERTY_TERMINAL_UNPROVED", result["pendingProofs"])
        self.assertIn(
            "FUTURE_BYTE_DERIVED_DECLARATION_CONSUMER_ABSENT",
            result["pendingProofs"],
        )
        self.assertFalse(result["executionEligible"])

        for field, replacement in (
            ("kind", "OPAQUE_PROPERTY_AREA"),
            ("provenance", "TRUST_ME_PRIVATE_COPY"),
            ("originalSourceClass", "UNKNOWN_SOURCE"),
        ):
            malformed = copy.deepcopy(value)
            malformed["propertyInput"]["sources"][0][field] = replacement
            self.assertIn(
                "PROPERTY_SOURCE_SCHEMA_MISMATCH",
                self.validate(malformed)["findingCodes"],
                field,
            )

    def test_negative_corpus_is_complete_and_every_case_rejects(self) -> None:
        corpus = self.data["negativeCorpus"]
        self.assertEqual(len(corpus), 16)
        self.assertEqual(
            {item["caseId"] for item in corpus},
            {
                "duplicate-servicemanager",
                "duplicate-hwservicemanager",
                "baseline-nonplacement-role-removal",
                "multi-role-removal-disguised-as-one",
                "component-consumer-digest-drift",
                "global-selinuxfs-rw-bind",
                "global-selinux-load-write",
                "global-selinux-enforce-write",
                "native-global-binder-path",
                "relocated-native-global-binder-rdev",
                "sd-property-source",
                "cache-relocated-whole-snapshot",
                "private-snapshot-provenance-under-benign-path",
                "publicly-named-whole-snapshot",
                "native-global-property-service",
                "unknown-authority-exception-field",
            },
        )
        for case in corpus:
            self.assertEqual(
                case["expectedOutcome"],
                "REJECTED_FORBIDDEN_OR_MALFORMED_SURFACE",
            )
            self.assertTrue(
                set(case["expectedFindingCodes"]).issubset(case["actualFindingCodes"]),
                case["caseId"],
            )

    def test_unknown_fields_and_noncanonical_paths_fail_closed(self) -> None:
        value = copy.deepcopy(self.base)
        value["unreviewedException"] = True
        result = self.validate(value)
        self.assertEqual(result["findingCodes"], ["SCHEMA_KEY_MISMATCH"])
        self.assertFalse(result["surfacePolicySatisfied"])

        value = copy.deepcopy(self.base)
        value["selinuxSurface"]["operations"] = [
            {
                "kind": "OPEN",
                "source": None,
                "target": "/run/a90-wlan-capsule/../escape",
                "access": "READ",
                "scope": "CAPSULE_PRIVATE",
            }
        ]
        self.assertIn("NONCANONICAL_PATH_FORBIDDEN", self.validate(value)["findingCodes"])

    def test_malformed_scalar_and_enum_types_reject_without_exceptions(self) -> None:
        mutations = []

        value = copy.deepcopy(self.base)
        value["componentGraph"]["variantId"] = []
        mutations.append(value)

        value = copy.deepcopy(self.base)
        value["binderSurface"]["endpointMode"] = {}
        mutations.append(value)

        value = copy.deepcopy(self.base)
        value["propertyInput"]["sourceClass"] = []
        mutations.append(value)

        value = copy.deepcopy(self.base)
        value["propertyInput"]["finalTerminal"] = {}
        mutations.append(value)

        value = copy.deepcopy(self.base)
        value["propertyService"]["endpointMode"] = []
        mutations.append(value)

        value = copy.deepcopy(self.base)
        value["selinuxSurface"]["operations"] = [{
            "kind": [],
            "source": None,
            "target": "/run/a90-wlan-capsule/policy",
            "access": "READ",
            "scope": "CAPSULE_PRIVATE",
        }]
        mutations.append(value)

        binder = next(
            item
            for item in self.data["conditionalPrivateSurfaceExamples"]
            if item["exampleId"] == "private-binderfs-still-unproved"
        )["declaration"]
        value = copy.deepcopy(binder)
        value["binderSurface"]["endpoints"][0]["backingClass"] = []
        mutations.append(value)

        prop = next(
            item
            for item in self.data["conditionalPrivateSurfaceExamples"]
            if item["exampleId"] == "private-property-service-still-unproved"
        )["declaration"]
        value = copy.deepcopy(prop)
        value["propertyService"]["endpoints"][0]["namespaceScope"] = {}
        mutations.append(value)

        for index, malformed in enumerate(mutations):
            result = self.validate(malformed)
            self.assertFalse(result["surfacePolicySatisfied"], index)
            self.assertEqual(
                result["outcome"],
                "REJECTED_FORBIDDEN_OR_MALFORMED_SURFACE",
                index,
            )

    def test_execution_economy_is_serial_calibrated_and_not_authority(self) -> None:
        economy = self.data["executionEconomy"]
        units = economy["logicalFutureUnitProjection"]
        self.assertEqual(
            (
                units["correctedBaselineVariantAttemptsMax"],
                units["oneRoleRemovalUnits"],
                units["successfulRemovalFreshBaselineRequalificationsMax"],
                units["mutuallyExclusivePropertyTerminalAttemptsMax"],
                units["oneToOneSerialUnitProjection"],
            ),
            (2, 13, 13, 2, 30),
        )
        self.assertEqual(units["formula"], "2 + 13 + 13 + 2 = 30")
        self.assertFalse(economy["seriality"]["parallelExecutionAllowed"])
        calibration = economy["calibration"]
        self.assertEqual(calibration["wp2_2HostOnlyDeviceOrdinalConsumed"], 0)
        self.assertEqual(
            calibration["exactAttendedSessionCount"],
            "UNPROVED_UNTIL_WP2_5B_EXECUTION_PROCESS_EXISTS",
        )
        self.assertEqual(
            calibration["exactOrdinalBudget"],
            "UNSET_BLOCKS_EXECUTION_QUALIFICATION",
        )
        self.assertTrue(calibration["operatorAcceptanceRequiredBeforeExecutionQualification"])
        self.assertEqual(len(economy["earlyStopValue"]), 6)

    def test_reduction_claim_is_order_conditioned_not_minimal(self) -> None:
        scope = self.data["executionEconomy"]["resultScope"]
        self.assertEqual(scope["claim"], "ORDER_CONDITIONED_REDUCED_GENERATION_ONLY")
        self.assertIs(scope["globalMinimumProved"], False)
        self.assertIs(scope["terminalOneMinimalProved"], False)
        self.assertIs(scope["terminalRetestSweepIncludedInThirty"], False)
        self.assertIn("non-monotonic", scope["reason"])


if __name__ == "__main__":
    unittest.main()
