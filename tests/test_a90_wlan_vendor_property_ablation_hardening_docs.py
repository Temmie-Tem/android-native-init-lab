import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = (
    ROOT
    / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
)
EXPECTED_COLLECTION_SHA256 = (
    "1a9d4901e3b21b3fd4ec02f2a308e2faca5af228fbfd1956de1262e11c02fd47"
)

EVIDENCE_RELS = (
    "AGENTS.md",
    "GOAL_A90.md",
    "docs/operations/targets/A90_TARGET_CONTRACT.md",
    "docs/operations/CAMPAIGN_LEDGER_A90.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md",
    "docs/reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md",
    "docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md",
    "docs/reports/A90_H24_PERSISTENT_HUD_BOOTSTRAP_EINVAL_INCIDENT_2026-08-12.md",
    "docs/reports/A90_H16_PERSISTENT_DEBIAN_RETURN_OBSERVER_INCIDENT_2026-08-10.md",
    "docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md",
    "docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md",
    "docs/security/hardening/a90-debian-supervised-wlan-2026-08-15/proposals/debian-supervised-wlan.md",
    "docs/security/hardening/a90-sd-free-input-evidence-2026-08-15/proposals/typed-sd-free-input-evidence.md",
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h16/manifest.toml",
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml",
    "workspace/public/src/native-init/helpers/a90_android_execns_probe.c",
    "workspace/public/src/native-init/v724/90_main.inc.c",
    "docs/archive/legacy/reports/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_2026-05-18.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_2026-05-19.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V1692_CNSS_NONLOG_CONTROL_FLOW_2026-06-02.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V2033_WLANMDSP_TFTP_TRANSFER_COMPLETION_GAP_2026-06-04.md",
    "docs/archive/legacy/reports/NATIVE_INIT_V2117_DUAL_RFS_LEAF_ANDROID_IDENTITY_HANDOFF_2026-06-05.md",
)


def collection_sha256() -> str:
    aggregate = hashlib.sha256()
    for rel in EVIDENCE_RELS:
        data = (ROOT / rel).read_bytes()
        aggregate.update(rel.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(len(data)).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(hashlib.sha256(data).hexdigest().encode("ascii"))
        aggregate.update(b"\0")
    return aggregate.hexdigest()


class A90WlanVendorPropertyAblationHardeningDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads((ANALYSIS / "hardening.json").read_text())
        self.context = (ANALYSIS / "context.md").read_text()
        self.proposal = (
            ANALYSIS / "proposals/wlan-vendor-property-ablation.md"
        ).read_text()
        self.design = json.loads(
            (
                ANALYSIS
                / "design/a90-h24-wlan-one-factor-ablation-design-v1.json"
            ).read_text()
        )
        self.policy = json.loads(
            (
                ANALYSIS
                / "policy/a90-h24-wlan-forbidden-surface-policy-v1.json"
            ).read_text()
        )
        self.wp2_3_inventory = json.loads(
            (
                ANALYSIS
                / "inventory/a90-h24-wlan-dependency-surface-inventory-v1.json"
            ).read_text()
        )
        self.helper = (
            ROOT
            / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
        ).read_text()
        self.manifest = (
            ROOT
            / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml"
        ).read_text()

    def test_evidence_collection_is_exact_and_current(self) -> None:
        self.assertEqual(len(EVIDENCE_RELS), 24)
        self.assertEqual(collection_sha256(), EXPECTED_COLLECTION_SHA256)
        source = self.data["sourceEvidence"]
        self.assertEqual(source["artifactCount"], len(EVIDENCE_RELS))
        self.assertEqual(source["collectionSha256"], EXPECTED_COLLECTION_SHA256)
        self.assertEqual(source["sourceDrift"], "none")

    def test_analysis_is_h0_and_grants_no_authority(self) -> None:
        authority = self.data["authority"]
        self.assertEqual(authority["tier"], "H0")
        for key in (
            "candidateEligible",
            "deviceInstallAuthorized",
            "propertyProvisionAuthorized",
            "credentialProvisionAuthorized",
            "ufsMutationAuthorized",
            "sdRemovalAuthorized",
            "d0Authorized",
            "d1Authorized",
            "f1Authorized",
            "handoffAuthorized",
            "otherTargetEvidenceUsed",
            "otherTargetFileRead",
        ):
            self.assertIs(authority[key], False)
        self.assertEqual(authority["primaryPassPublicS22PathDisplayCount"], 1)
        self.assertEqual(authority["s20plusContactCount"], 0)
        self.assertIn("creates no candidate identity", self.proposal)
        self.assertFalse((ANALYSIS / "implementation").exists())

    def test_selected_h24_mode_and_duplicate_pair_are_bound(self) -> None:
        self.assertIn(
            "-DA90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER=1",
            self.manifest,
        )
        self.assertIn("/mnt/sdext/a90/private-property-v317", self.manifest)

        function = self.helper[
            self.helper.index("static int run_wifi_companion_start_only_guarded") :
            self.helper.index("static int run_wifi_companion_hal_order_start_only_guarded")
        ]
        first_pair = function[
            function.index("if (!android_order_pre_cnss_provider_observer &&\n        with_service_manager") :
            function.index("if (!android_order_pre_cnss_provider_observer &&\n        !peripheral_manager_node_parity")
        ]
        second_pair = function[
            function.index("if (wlan_pd_service_window_trigger || wlan_pd_service_object_visible_trigger)") :
            function.index("if (wlan_pd_pm_service_window_trigger || wlan_pd_service_object_visible_trigger)")
        ]
        for target in (
            '"/system/bin/servicemanager"',
            '"/system/bin/hwservicemanager"',
        ):
            self.assertEqual(first_pair.count(target), 1)
            self.assertEqual(second_pair.count(target), 1)

        entries = (
            "servicemanager",
            "hwservicemanager",
            "qrtr_ns",
            "pd_mapper",
            "rmt_storage",
            "tftp_server",
            "servicemanager",
            "hwservicemanager",
            "vndservicemanager",
            "pm_proxy_helper",
            "per_mgr",
            "cnss_diag",
            "cnss_daemon",
        )
        self.assertEqual(len(entries), 13)
        self.assertEqual(len(set(entries)), 11)
        self.assertIn("thirteen entries representing eleven unique roles", self.proposal)
        self.assertIn("published order hides the duplicate pair", self.proposal)

    def test_current_liveness_policy_is_not_mislabeled_as_necessity(self) -> None:
        self.assertIn("persistent_handoff_child_required", self.helper)
        self.assertIn("identity != COMPOSITE_ID_MACLOADER", self.helper)
        self.assertEqual(
            self.data["assessment"]["propertyVerdict"],
            "UNPROVED",
        )
        self.assertIn("Individually proved hardware-essential roles: **zero**", (
            ANALYSIS / "hardening.md"
        ).read_text())
        self.assertIn("Individually proved unrelated roles: **zero**", (
            ANALYSIS / "hardening.md"
        ).read_text())
        self.assertIn("neither live-qualified nor known-minimal", self.proposal)

    def test_global_selinux_mutation_is_explicitly_rejected(self) -> None:
        for source_fact in (
            'bind_rw("/sys/fs/selinux", paths->sys_fs_selinux)',
            "load_precompiled_policy_for_pm_observer(paths, stdout_buf)",
            "write_file_once_to_fd(policy_path, load_fd",
            'write(enforce_fd, "0", 1)',
        ):
            self.assertIn(source_fact, self.helper)
        self.assertIn("zero writes to SELinux policy `load`, `enforce`", self.proposal)
        self.assertIn(
            "global selinux load",
            self.data["assessment"]["globalPolicyVerdict"].replace("_", " ").lower(),
        )

    def test_property_has_only_two_acceptable_terminals(self) -> None:
        self.assertIn("property_service_shim_needed", self.helper)
        self.assertIn("PROPERTY_ABSENT_PROVED", self.proposal)
        self.assertIn("PROPERTY_FINITE_SEED_PROVED", self.proposal)
        self.assertIn("The current whole snapshot", self.context)
        self.assertIn("write acknowledgements", self.context)
        self.assertNotIn("PROPERTY_MINIMAL_SEED_ASSUMED", self.proposal)

    def test_options_and_tradeoffs_are_complete(self) -> None:
        opportunity = self.data["opportunities"][0]
        self.assertEqual(
            opportunity["recommendedOptionId"],
            "topology-neutral-ablation-first",
        )
        self.assertEqual(
            {option["optionId"] for option in opportunity["options"]},
            {
                "rehost-h24-unchanged",
                "reduced-native-supervisor",
                "debian-supervised-capsule",
                "topology-neutral-ablation-first",
            },
        )
        required = {
            "security",
            "performance",
            "memory",
            "reliability",
            "operability",
            "migration",
        }
        for option in opportunity["options"]:
            self.assertEqual(
                {tradeoff["dimension"] for tradeoff in option["tradeoffs"]},
                required,
            )
            self.assertTrue(option["evidenceCoverage"])
            for diagram in option["diagramPaths"].values():
                text = (ANALYSIS / diagram).read_text()
                self.assertTrue(text.startswith("flowchart LR\n"))
                self.assertIn("boundary", text.lower())

    def test_ablation_sequence_and_metrics_are_explicit(self) -> None:
        stages = (
            "`A0`", "`A1`", "`A2`", "`A3`", "`A4`",
            "`A5a`", "`A5b`", "`A6a`", "`A6b`", "`A6c`",
            "`A7a`", "`A7b`", "`A7c`", "`A7d`",
            "`A8`", "`A9`", "`A10`", "`A11a`", "`A11b`",
            "`A12`", "`A13`",
        )
        for stage in stages:
            self.assertIn(stage, self.proposal)
        self.assertEqual(
            [self.proposal.index(f"| {stage} |") for stage in stages],
            sorted(self.proposal.index(f"| {stage} |") for stage in stages),
        )
        self.assertLess(
            self.proposal.index("| `A2` | Eliminate global SELinux mutation"),
            self.proposal.index("| `A4` | Remove `cnss_diag` only"),
        )
        for component_terminal in (
            "Remove `cnss-daemon` only",
            "Remove modem holder only",
            "Remove property-service shim only",
        ):
            self.assertIn(component_terminal, self.proposal)
        for phrase in (
            "One ablation changes one variable",
            "A failure is terminal evidence for that unit",
            "process/thread/FD count",
            "RSS/PSS",
            "CPU time",
            "wakeups",
            "property/IPC",
            "cleanup",
            "recovery",
        ):
            self.assertIn(phrase, self.proposal)

    def test_current_source_launch_inventory_is_complete(self) -> None:
        self.assertIn("### Current-source launch inventory", self.proposal)
        ordered_roles = (
            "| 1 `servicemanager` #1 |",
            "| 2 `hwservicemanager` #1 |",
            "| 3 `qrtr_ns` |",
            "| 4 `pd_mapper` |",
            "| 5 `rmt_storage` |",
            "| 6 `tftp_server` |",
            "| 7 `servicemanager` #2 |",
            "| 8 `hwservicemanager` #2 |",
            "| 9 `vndservicemanager` |",
            "| 10 `pm_proxy_helper` |",
            "| 11 `per_mgr` |",
            "| 12 `cnss_diag` |",
            "| 13 `cnss_daemon` |",
        )
        for role in ordered_roles:
            self.assertIn(role, self.proposal)
        for required_fact in (
            "UID/GID `2906:2906`",
            "groups `1000,3009`",
            "groups `3003,3005,1010`",
            "groups `1000,1010,3003,1015,1023,2002`",
            "exact post-exec caps are **UNPROVED**",
            "android-init-root` capability mode",
            "process-group `SIGTERM`",
            "property-service shim",
            "modem holder",
            "13 composite children + shim + holder + helper",
            "construction `:58654-58666`",
            "cleanup `:61426-61500`",
            "cleanup `:29166-29266`",
            "`/bin/a90_android_execns_probe`",
            "/cache/native-init-wifi-test-boot-v2812-helper.result",
            "/cache/native-init-wifi-test-boot-v2812.ready",
            "complete selected argv and",
        ):
            self.assertIn(required_fact, self.proposal)

    def test_dependency_classification_and_property_diagram_are_fail_closed(self) -> None:
        for phrase in (
            "### Dependency classification: established versus unproved",
            "producer is the external whole property snapshot",
            "write-compatibility shim",
            "compatibility registry/context-manager route",
            "QMI | protocol/transport observation surface",
            "contains no separately named `rmtfs` daemon",
            "relationship between `rmt_storage` and `rmtfs` is **UNPROVED**",
            "diagnostic candidate",
            "does not rename `rmt_storage` as `rmtfs`",
        ):
            self.assertIn(phrase, self.proposal)
        before = (
            ANALYSIS / "diagrams/wlan-vendor-property-ablation-before.mmd"
        ).read_text()
        self.assertIn(
            'SD["SD property snapshot"] --> R["Vendor property readers"]',
            before,
        )
        self.assertIn('P -. "write ACK only; no proved property-area mutation" .-> C', before)
        self.assertNotIn('SD["SD property snapshot"] --> P', before)

    def test_wp_h0_1_generated_inventory_stays_fail_closed(self) -> None:
        inventory_path = (
            ANALYSIS
            / "inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json"
        )
        inventory = json.loads(inventory_path.read_text())
        self.assertEqual(
            inventory["status"]["wpH01PublicSourceInventory"],
            "COMPLETE_FROZEN_H24_SELECTED_PATH_ONLY",
        )
        self.assertEqual(
            inventory["status"]["wpH01Overall"],
            "PARTIAL_RUNTIME_CLOSURE_BLOCKED",
        )
        self.assertEqual(
            self.data["assessment"]["wpH01PublicSourceInventory"],
            inventory["status"]["wpH01PublicSourceInventory"],
        )
        self.assertEqual(
            self.data["assessment"]["wpH01Overall"],
            inventory["status"]["wpH01Overall"],
        )
        self.assertEqual(
            inventory["status"]["wpH01OpaqueRuntimeClosure"],
            "BLOCKED_UNPROVED",
        )
        self.assertEqual(len(inventory["dependencyGates"]), 10)
        self.assertTrue(
            all(gate["status"] == "UNPROVED" for gate in inventory["dependencyGates"])
        )
        self.assertIn("H0D01-H0D10", self.proposal)
        self.assertIn("`WP-H0-2` **design** is now complete as H0", self.proposal)
        self.assertIn("cannot be retired by\none offline generation", self.proposal)
        self.assertIn("Option C is still research-only", (ANALYSIS / "hardening.md").read_text())

    def test_wp_h0_2_design_boundary_is_complete_but_not_executable(self) -> None:
        assessment = self.data["assessment"]
        self.assertEqual(assessment["wpH02Design"], "COMPLETE_H0_DESIGN_ONLY")
        self.assertEqual(
            assessment["wpH02DesignPath"],
            "design/a90-h24-wlan-one-factor-ablation-design-v1.json",
        )
        self.assertEqual(assessment["wpH02CorrectedHealthyBaseline"], "ABSENT_UNPROVED")
        self.assertEqual(assessment["wpH02ExecutionQualification"], "ABSENT")
        self.assertIs(assessment["wpH02LiveAuthority"], False)
        self.assertEqual(self.design["status"]["wpH02Design"], "COMPLETE_H0_DESIGN_ONLY")
        self.assertEqual(self.design["stateMachine"]["currentReachableTransitions"], [])
        self.assertIs(self.design["authority"]["liveExecutionAuthorized"], False)
        self.assertIn("H24 is **not** an ablation baseline", self.proposal)
        self.assertIn("SD_FREE_PUBLIC_BOOTSTRAP_SUPERSET_PROVED", self.proposal)
        self.assertIn("REMOVAL_SUPPORTED_FOR_GENERATION", self.proposal)
        self.assertIn("NO_PROOF_OBSERVER", self.proposal)
        self.assertNotIn("with identical remaining\nbytes", self.proposal)
        self.assertIn("Observer/parser failure and device functional failure", self.proposal)
        diagram = (
            ANALYSIS / "diagrams/wlan-vendor-property-ablation-state-machine.mmd"
        ).read_text()
        self.assertTrue(diagram.startswith("flowchart LR\n"))
        self.assertIn("H0 design only", diagram)
        self.assertIn("never replay", diagram)
        self.assertIn("Permanent boundary retained", diagram)
        self.assertIn("One exact variant failed", diagram)
        self.assertIn("only after the other separately bound variant also fails", diagram)
        self.assertIn("Both exact variant failures bound", diagram)
        self.assertIn("pre-effect health only; never admits G0", diagram)
        self.assertIn("BASELINE_ADMITTED_G0", diagram)
        aggregate = self.design["baselineFormation"]["aggregateDecisionModel"]
        self.assertEqual(len(aggregate["decisionTable"]), 16)
        self.assertEqual(
            sum(
                any(
                    decision["aggregateOutcome"] == "NO_GO_ABLATION_BASELINE"
                    for decision in row["attemptOrderDecisions"]
                )
                for row in aggregate["decisionTable"]
            ),
            1,
        )

    def test_wp2_2_static_policy_corpus_and_execution_economy_are_bound(self) -> None:
        assessment = self.data["assessment"]
        self.assertEqual(
            assessment["wp2_2Policy"],
            "COMPLETE_H0_STATIC_POLICY_AND_NEGATIVE_CORPUS_ONLY",
        )
        self.assertEqual(
            assessment["wp2_2PolicyPath"],
            "policy/a90-h24-wlan-forbidden-surface-policy-v1.json",
        )
        self.assertEqual(assessment["wp2_2NegativeCaseCount"], 16)
        self.assertEqual(assessment["wp2_2FutureByteDerivationConsumer"], "ABSENT")
        self.assertEqual(assessment["wp2_2LogicalSerialUnitProjection"], 30)
        self.assertEqual(assessment["wp2_2HostOnlyDeviceOrdinalConsumed"], 0)
        self.assertEqual(
            assessment["wp2_2ExactOrdinalBudget"],
            "UNSET_BLOCKS_EXECUTION_QUALIFICATION",
        )
        self.assertEqual(
            assessment["wp2_2ResultScope"],
            "ORDER_CONDITIONED_REDUCED_GENERATION_ONLY",
        )
        self.assertEqual(
            self.policy["status"]["wp2_2"],
            assessment["wp2_2Policy"],
        )
        self.assertEqual(self.policy["status"]["dependencyGatesRetired"], [])
        self.assertEqual(len(self.policy["negativeCorpus"]), 16)
        self.assertEqual(
            self.policy["executionEconomy"]["logicalFutureUnitProjection"]
            ["oneToOneSerialUnitProjection"],
            30,
        )
        self.assertFalse(
            self.policy["executionEconomy"]["seriality"]
            ["parallelExecutionAllowed"]
        )
        self.assertIn("## WP2-2 Forbidden-Surface Policy And Execution Economy", self.proposal)
        self.assertIn("2 + 13 + 13 + 2 = 30", self.proposal)
        self.assertIn("consumes zero device ordinals", self.proposal)
        self.assertIn("not yet a proved attended-session count", self.proposal)
        self.assertIn("even terminal one-minimality is\nunproved", self.proposal)
        self.assertIn("no byte-derived future consumer", self.proposal)
        self.assertIn("complete source-derived ordered\nfourteen-instance graph", self.proposal)
        self.assertIn("qualified\nbyte-derived lineage consumer", self.proposal)

    def test_wp2_3_inventory_preserves_known_historical_and_unproved_states(self) -> None:
        assessment = self.data["assessment"]
        self.assertEqual(
            assessment["wp2_3Inventory"],
            "COMPLETE_H0_REQUIREMENT_AND_EVIDENCE_STATE_INVENTORY_ONLY",
        )
        self.assertEqual(
            assessment["wp2_3InventoryPath"],
            "inventory/a90-h24-wlan-dependency-surface-inventory-v1.json",
        )
        self.assertEqual(assessment["wp2_3RoleCount"], 14)
        self.assertEqual(assessment["wp2_3DependencySurfaceSlotCount"], 140)
        self.assertEqual(assessment["wp2_3CurrentH24ExactOpaqueElfBindingCount"], 0)
        self.assertEqual(assessment["wp2_3NegativeCaseCount"], 10)
        self.assertEqual(assessment["wp2_3DependencyGatesRetired"], [])
        self.assertEqual(assessment["wp2_3FutureByteDerivedConsumer"], "ABSENT")
        self.assertEqual(
            self.wp2_3_inventory["status"]["wp2_3"],
            assessment["wp2_3Inventory"],
        )
        self.assertEqual(self.wp2_3_inventory["counts"]["roleRecords"], 14)
        self.assertEqual(
            self.wp2_3_inventory["counts"]["dependencySurfaceSlots"], 140
        )
        self.assertIn("## WP2-3 Dependency-Surface Inventory Boundary", self.proposal)
        self.assertIn("current H24 exact opaque-ELF bindings remain\n**zero**", self.proposal)
        self.assertIn("HISTORICAL_ONLY_H24_APPLICABILITY_UNPROVED", self.proposal)
        self.assertIn("`H0D01-H0D10` all remain `UNPROVED`", self.proposal)
        self.assertIn("`WP2-4` may now design", self.proposal)

    def test_prior_portfolio_correction_is_locked(self) -> None:
        prior = (
            ROOT
            / "docs/security/hardening/a90-debian-supervised-wlan-2026-08-15/proposals/debian-supervised-wlan.md"
        ).read_text()
        self.assertIn("thirteen child entries representing eleven", prior)
        self.assertRegex(prior, r"neither\s+live-qualified nor known-minimal")
        self.assertNotIn("Inferred: that list is known-sufficient", prior)
        self.assertNotIn("Which of the eleven H24 children", prior)
        typed = (
            ROOT
            / "docs/security/hardening/a90-sd-free-input-evidence-2026-08-15/proposals/typed-sd-free-input-evidence.md"
        ).read_text()
        self.assertNotIn("known-sufficient", typed)

    def test_proposal_headings_and_relative_links_are_complete(self) -> None:
        headings = (
            "## Decision",
            "## Executive Recommendation",
            "## Evidence",
            "## Current Design And Failure Mode",
            "## Desired Invariants",
            "## Constraints And Non-Goals",
            "## Before Architecture",
            "## Property And IPC Boundary",
            "## Options",
            "## Comparison",
            "## Recommendation",
            "## Ablation Matrix",
            "## WP-H0-2 One-Factor Design Boundary",
            "## Evidence Coverage And Residual Risk",
            "## Migration And Rollout",
            "## Validation Plan",
            "## Implementation Work Packages",
            "## Open Questions",
            "## Authority",
        )
        positions = [self.proposal.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        for evidence_id in range(1, 17):
            self.assertIn(f"`E{evidence_id:02d}`", self.proposal)

        for markdown in ANALYSIS.rglob("*.md"):
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", markdown.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(resolved.exists(), f"broken link in {markdown}: {target}")


if __name__ == "__main__":
    unittest.main()
