import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs/security/hardening/a90-debian-supervised-wlan-2026-08-15"
EXPECTED_COLLECTION_SHA256 = (
    "b2d61c52455603583f19fc8f005e16597523ef82cb7e474e843e6df13828bcdf"
)

EVIDENCE_RELS = (
    "AGENTS.md",
    "GOAL_A90.md",
    "docs/operations/targets/A90_TARGET_CONTRACT.md",
    "docs/operations/CAMPAIGN_LEDGER_A90.md",
    "docs/reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md",
    "docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md",
    "docs/reports/A90_ISOLATED_DEBIAN_SECURITY_DERIVATION_H0_2026-08-15.md",
    "docs/plans/A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md",
    "docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md",
    "docs/plans/A90_ATOMIC_WIFI_OWNERSHIP_DIAGNOSTIC_RESIDENT_DESIGN_2026-08-14.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA14_LINKSTATE_SCAN_BLOCKED_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA20_NATIVE_SERVICE_BOUNDARY_PASS_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA22_NATIVE_SERVICE_CLIENT_LIVE_PASS_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA23_UPLINK_SERVICE_LIVE_PASS_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA24_UPLINK_CLIENT_LIVE_PASS_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA31_NATIVE_SCAN_RECOVERY_V3388_LIVE_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA40_WSTA41_MATERIALIZATION_CONFIRMED_AUTOCONNECT_PASS_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA42_NATIVE_UPLINK_DPUBLIC_TUNNEL_PASS_2026-07-04.md",
    "docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA43_ORCHESTRATED_NATIVE_UPLINK_DPUBLIC_PASS_2026-07-04.md",
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml",
    "workspace/public/src/native-init/helpers/a90_android_execns_probe.c",
    "workspace/public/src/native-init/v724/90_main.inc.c",
    "workspace/public/src/native-init/a90_server_distro.c",
    "workspace/public/src/native-init/a90_config.h",
    "workspace/public/src/scripts/server-distro/a90_isolated_debian_security_derivation.py",
    "tests/test_a90_isolated_debian_security_derivation.py",
)


def collection_sha256() -> str:
    aggregate = hashlib.sha256()
    for rel in EVIDENCE_RELS:
        path = ROOT / rel
        data = path.read_bytes()
        aggregate.update(rel.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(len(data)).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(hashlib.sha256(data).hexdigest().encode("ascii"))
        aggregate.update(b"\0")
    return aggregate.hexdigest()


class A90DebianSupervisedWlanHardeningDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads((ANALYSIS / "hardening.json").read_text())
        self.proposal = (
            ANALYSIS / "proposals/debian-supervised-wlan.md"
        ).read_text()

    def test_evidence_collection_is_exact_and_current(self) -> None:
        self.assertEqual(len(EVIDENCE_RELS), 28)
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
            "d0Authorized",
            "d1Authorized",
            "f1Authorized",
            "handoffAuthorized",
            "otherTargetsTouched",
        ):
            self.assertIs(authority[key], False)
        portfolio = (ANALYSIS / "hardening.md").read_text()
        self.assertIn("creates no identity, artifact, qualification", portfolio)
        self.assertIn("H24 remains installed", portfolio)

    def test_portfolio_has_three_real_options_and_a_conditional_recommendation(self) -> None:
        opportunity = self.data["opportunities"][0]
        self.assertEqual(opportunity["opportunityId"], "debian-supervised-wlan")
        option_ids = {option["optionId"] for option in opportunity["options"]}
        self.assertEqual(
            option_ids,
            {
                "native-supervisor-isolated-debian",
                "clean-prelaunch-debian-adoption",
                "clean-debian-relaunch",
            },
        )
        self.assertEqual(
            opportunity["recommendedOptionId"],
            "native-supervisor-isolated-debian",
        )
        self.assertIn("H0 feasibility program", opportunity["recommendation"])

    def test_every_option_has_required_tradeoffs_and_diagrams(self) -> None:
        required = {
            "security",
            "performance",
            "memory",
            "reliability",
            "operability",
            "migration",
        }
        for option in self.data["opportunities"][0]["options"]:
            self.assertEqual(
                {tradeoff["dimension"] for tradeoff in option["tradeoffs"]},
                required,
            )
            self.assertTrue(option["evidenceCoverage"])
            for diagram in option["diagramPaths"].values():
                text = (ANALYSIS / diagram).read_text()
                self.assertTrue(text.startswith("flowchart LR\n"))
                self.assertIn("boundary", text.lower())

    def test_proposal_headings_and_evidence_labels_are_complete(self) -> None:
        headings = (
            "## Decision",
            "## Executive Recommendation",
            "## Evidence",
            "## Current Design And Failure Mode",
            "## Desired Invariants",
            "## Constraints And Non-Goals",
            "## Before Architecture",
            "## Options",
            "## Comparison",
            "## Recommendation",
            "## Evidence Coverage And Residual Risk",
            "## Migration And Rollout",
            "## Validation Plan",
            "## Implementation Work Packages",
            "## Open Questions",
        )
        positions = [self.proposal.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))
        for evidence_id in range(1, 12):
            self.assertIn(f"`E{evidence_id:02d}`", self.proposal)

    def test_current_h24_is_not_mislabeled_as_the_minimum(self) -> None:
        manifest = (
            ROOT
            / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml"
        ).read_text()
        helper = (
            ROOT
            / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
        ).read_text()
        main = (
            ROOT / "workspace/public/src/native-init/v724/90_main.inc.c"
        ).read_text()
        self.assertIn("-DA90_WIFI_PERSISTENT_HANDOFF_V1=1", manifest)
        self.assertIn(
            "-DA90_WIFI_TEST_BOOT_WLAN_PD_SERVICE_OBJECT_VISIBLE_TRIGGER=1",
            manifest,
        )
        self.assertIn("/mnt/sdext/a90/private-property-v317", manifest)
        self.assertIn(
            "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,pm_proxy_helper,per_mgr,vndservice_query,subsys_modem_holder,cnss_diag,cnss_daemon,service-object-visible-summary",
            helper,
        )
        self.assertIn("property_service_shim_needed", helper)
        self.assertIn("persistent_handoff_modem_holder_ready", helper)
        self.assertIn("a90_wifi_start_boot_autoconnect_once", main)
        self.assertRegex(
            self.proposal,
            r"neither\s+live-qualified nor known-minimal",
        )
        self.assertIn(
            "thirteen child entries representing eleven unique roles",
            self.proposal,
        )
        self.assertRegex(
            self.proposal,
            r"`servicemanager` and `hwservicemanager` are each\s+enqueued twice",
        )

    def test_single_owner_does_not_collapse_the_remote_trust_boundary(self) -> None:
        self.assertIn(
            "one PID 1 owns their lifecycle, evidence, network policy, and recovery",
            self.proposal,
        )
        self.assertIn("rootless service identity", self.proposal)
        self.assertIn("workload sandbox", self.proposal)
        self.assertIn(
            "Neither a rootfs key nor a supplicant config alone", self.proposal
        )
        self.assertFalse((ANALYSIS / "implementation").exists())

    def test_relative_markdown_links_resolve(self) -> None:
        markdown_files = tuple(ANALYSIS.rglob("*.md"))
        self.assertGreaterEqual(len(markdown_files), 3)
        for markdown in markdown_files:
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", markdown.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(resolved.exists(), f"broken link in {markdown}: {target}")


if __name__ == "__main__":
    unittest.main()
