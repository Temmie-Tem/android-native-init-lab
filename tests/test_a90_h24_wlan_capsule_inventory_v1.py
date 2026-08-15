import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = (
    ROOT
    / "workspace/public/src/scripts/revalidation/a90_h24_wlan_capsule_inventory_v1.py"
)
INVENTORY = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
    / "inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json"
)


def load_generator():
    spec = importlib.util.spec_from_file_location("a90_h24_wlan_inventory", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load inventory generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A90H24WlanCapsuleInventoryV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = INVENTORY.read_text()
        cls.data = json.loads(cls.text)
        cls.generator = load_generator()

    def test_checked_inventory_is_canonical_generator_output(self) -> None:
        self.assertEqual(self.text, self.generator.canonical_text())
        subprocess.run(
            [sys.executable, str(GENERATOR), "--check", str(INVENTORY)],
            cwd=ROOT,
            check=True,
        )
        self.assertEqual(self.text, json.dumps(self.data, indent=2, sort_keys=True) + "\n")

    def test_source_pins_are_current_regular_public_files(self) -> None:
        pins = self.data["sourcePins"]
        self.assertEqual(len(pins), 9)
        self.assertEqual([pin["path"] for pin in pins], list(self.generator.SOURCE_RELS))
        for pin in pins:
            path = ROOT / pin["path"]
            self.assertTrue(path.is_file())
            self.assertFalse(path.is_symlink())
            raw = path.read_bytes()
            self.assertEqual(pin["bytes"], len(raw))
            self.assertEqual(pin["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertNotIn("workspace/private", pin["path"])

    def test_authority_is_h0_only(self) -> None:
        authority = self.data["authority"]
        self.assertEqual(authority["tier"], "H0")
        for key, value in authority.items():
            if key == "tier":
                continue
            self.assertIs(value, False, key)
        self.assertNotIn("workspace/private", self.text)

    def test_selected_graph_is_exactly_thirteen_eleven_and_sixteen(self) -> None:
        counts = self.data["counts"]
        self.assertEqual(counts["compositeInstances"], 13)
        self.assertEqual(counts["uniqueCompositeRoles"], 11)
        self.assertEqual(counts["helperManagedChildrenOutsideComposite"], 2)
        self.assertEqual(counts["topologyOwners"], 1)
        self.assertEqual(counts["sourceAccountedProcessesBeforeStationPolicy"], 16)

        composite = [
            item for item in self.data["components"] if item["kind"] == "composite-child"
        ]
        self.assertEqual(len(composite), 13)
        self.assertEqual(len({item["role"] for item in composite}), 11)
        self.assertEqual([item["order"] for item in composite], list(range(1, 14)))
        self.assertEqual(
            self.data["constructionDefects"]["duplicateRoles"],
            {
                "hwservicemanager": ["hwservicemanager#1", "hwservicemanager#2"],
                "servicemanager": ["servicemanager#1", "servicemanager#2"],
            },
        )
        derived = self.generator.derive_selected_composite_graph()
        self.assertEqual(
            [(item["role"], item["executable"], item["compositeIdentity"]) for item in composite],
            derived,
        )
        self.assertTrue(
            all(item["constructionEvidence"] == "source-parsed-selected-branch" for item in composite)
        )

    def test_selected_graph_parser_rejects_insert_remove_and_path_drift(self) -> None:
        helper = (ROOT / self.generator.SOURCE_RELS[1]).read_text()
        call = (
            'composite_child_init(&children[child_count++],\n'
            '                                 "pm_proxy_helper",\n'
            '                                 "/vendor/bin/pm_proxy_helper",\n'
            '                                 COMPOSITE_ID_PER_PROXY_HELPER);'
        )
        self.assertIn(call, helper)
        with self.assertRaises(ValueError):
            self.generator.components(helper.replace(call, call + "\n" + call, 1))
        with self.assertRaises(ValueError):
            self.generator.components(helper.replace(call, "", 1))
        with self.assertRaises(ValueError):
            self.generator.components(
                helper.replace(
                    call,
                    call.replace("/vendor/bin/pm_proxy_helper", "/vendor/bin/pm_proxy_helper.drift"),
                    1,
                )
            )

    def test_every_component_has_identity_lifetime_cleanup_and_anchors(self) -> None:
        self.assertEqual(len(self.data["components"]), 16)
        for component in self.data["components"]:
            for field in (
                "instanceId",
                "role",
                "kind",
                "executable",
                "argv",
                "launchPredicate",
                "identity",
                "ownershipPlane",
                "lifetime",
                "cleanup",
                "sourceAnchors",
                "opaqueRuntimeDependencyStatus",
            ):
                self.assertIn(field, component, f"{component.get('instanceId')}: {field}")
            self.assertTrue(component["sourceAnchors"])
            self.assertEqual(component["opaqueRuntimeDependencyStatus"], "UNPROVED")

    def test_auxiliary_and_topology_launch_contracts_are_exactly_bounded(self) -> None:
        by_id = {item["instanceId"]: item for item in self.data["components"]}
        shim = by_id["property-service-shim#1"]
        self.assertEqual(shim["launchContractState"], "SOURCE_DERIVED_SELECTED_BRANCH")
        self.assertIn("property_root != NULL", shim["launchPredicate"])
        self.assertTrue(shim["selectedPredicateEvaluation"]["result"])

        holder = by_id["modem-holder#1"]
        self.assertIn("wlan_pd_service_object_provider_seen", holder["launchPredicate"])
        self.assertTrue(holder["selectedPredicateEvaluation"]["requiresProviderSeen"])

        owner = by_id["wifi-helper#1"]
        self.assertEqual(owner["executable"], "/bin/a90_android_execns_probe")
        self.assertEqual(owner["argv"][0], owner["executable"])
        self.assertIn("wifi-companion-wlan-pd-service-object-visible-trigger-start-only", owner["argv"])
        self.assertIn("/cache/native-init-wifi-test-boot-v2812-helper.result", owner["argv"])
        self.assertIn("/cache/native-init-wifi-test-boot-v2812.ready", owner["argv"])
        self.assertNotIn("--allow-qrtr-ns-readback", owner["argv"])
        self.assertEqual(owner["environment"], [
            "PATH=/bin:/cache/bin:/system/bin:/vendor/bin",
            "HOME=/",
            "TERM=vt100",
        ])
        self.assertEqual(owner["launchContract"]["timeoutMs"], 0)
        self.assertEqual(owner["launchContract"]["stopTimeoutMs"], 1000)

    def test_historical_evidence_is_not_promoted_to_h24_runtime_fact(self) -> None:
        findings = self.data["historicalPublicEvidence"]
        self.assertEqual(len(findings), 5)
        self.assertTrue(
            all(item["evidenceState"] == "observed-historical" for item in findings)
        )
        self.assertTrue(
            all(item["h24Applicability"] != "PROVED" for item in findings)
        )
        self.assertIn(
            "IDENTITY_CONFLICT_REQUIRES_RESOLUTION",
            {item["h24Applicability"] for item in findings},
        )

    def test_all_ten_dependency_surfaces_remain_fail_closed(self) -> None:
        gates = self.data["dependencyGates"]
        self.assertEqual([gate["gateId"] for gate in gates], [f"H0D{i:02d}" for i in range(1, 11)])
        self.assertTrue(all(gate["status"] == "UNPROVED" for gate in gates))
        self.assertTrue(all(gate["wpH02DesignBlocking"] is False for gate in gates))
        self.assertTrue(all(gate["liveExecutionAuthorized"] is False for gate in gates))
        by_id = {gate["gateId"]: gate for gate in gates}
        self.assertEqual(
            by_id["H0D01"]["preExecutionRequirement"],
            "RETIRE_RELEVANT_ROW_BEFORE_EXECUTION",
        )
        self.assertEqual(
            by_id["H0D04"]["preExecutionRequirement"],
            "BOUNDED_EXECUTION_PRODUCES_RETIREMENT_EVIDENCE_NOT_A_PRECONDITION",
        )
        self.assertEqual(
            by_id["H0D10"]["preExecutionRequirement"],
            "PROVE_SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_BEFORE_EXECUTION_THEN_FREEZE_RETAINED_SET_AFTER_ABLATION",
        )
        self.assertEqual(
            by_id["H0D10"]["preExecutionHalf"]["requiredTerminal"],
            "SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED",
        )
        self.assertEqual(
            by_id["H0D10"]["postAblationHalf"]["acceptedTerminals"],
            ["PROPERTY_ABSENT_PROVED", "PROPERTY_FINITE_SEED_PROVED"],
        )
        self.assertIn("No future baseline", by_id["H0D10"]["preExecutionHalf"]["rule"])
        self.assertEqual(
            {gate["retirementClass"] for gate in gates},
            {
                "OFFLINE_STATIC",
                "HYBRID_STATIC_AND_OBSERVATION",
                "RUNTIME_OBSERVATION_AND_ABLATION",
                "RUNTIME_OBSERVATION",
                "SPLIT_PREEXECUTION_AND_POST_ABLATION_STATIC_FREEZE",
            },
        )
        self.assertEqual(
            {gate["surface"] for gate in gates},
            {
                "exact-elf-closure",
                "dynamic-dispatch",
                "configuration",
                "property-read-write",
                "binder",
                "qrtr-qmi",
                "device-kernel",
                "firmware-rfs",
                "writable-output",
                "sd-free-provenance",
            },
        )

    def test_option_c_cannot_advance_to_implementation(self) -> None:
        status = self.data["status"]
        self.assertEqual(
            status["wpH01PublicSourceInventory"],
            "COMPLETE_FROZEN_H24_SELECTED_PATH_ONLY",
        )
        self.assertEqual(status["wpH01Overall"], "PARTIAL_RUNTIME_CLOSURE_BLOCKED")
        self.assertEqual(status["wpH01OpaqueRuntimeClosure"], "BLOCKED_UNPROVED")
        self.assertEqual(status["optionC"], "H0_RESEARCH_ONLY_NOT_IMPLEMENTATION_ELIGIBLE")
        sequence = self.data["nextSequencingConstraint"]
        self.assertEqual(sequence["wpH02Design"], "ALLOWED_H0_ONLY_FROM_THIS_FROZEN_BLOCKER_REGISTRY")
        self.assertIn("row-specific", sequence["beforeWpH02Execution"])
        self.assertIn("H0D01 through H0D10", sequence["beforeOptionCImplementationOrPromotion"])
        self.assertIn("no single offline generation", sequence["beforeOptionCImplementationOrPromotion"])
        self.assertIn("blocks candidate identity allocation", sequence["failureRule"])

    def test_ownership_plane_map_keeps_recovery_external(self) -> None:
        planes = {item["plane"]: item for item in self.data["ownershipPlanes"]}
        self.assertEqual(len(planes), 5)
        self.assertEqual(
            planes["station scan, association, and DHCP"]["status"],
            "UNPROVED",
        )
        recovery = planes["boot rollback and physical recovery"]
        self.assertEqual(recovery["optionCRequiredOwner"], "unchanged external safety boundary")
        self.assertEqual(recovery["status"], "PERMANENT_BOUNDARY")


if __name__ == "__main__":
    unittest.main()
