from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "docs/security/hardening/a90-sd-free-input-evidence-2026-08-15"
EXPECTED_COLLECTION_SHA256 = (
    "89606178bd9a1753a4baa40a26d8a44bd7b34feed177449795925cf17911a474"
)

EVIDENCE_RELS = (
    "AGENTS.md",
    "GOAL_A90.md",
    "docs/operations/targets/A90_TARGET_CONTRACT.md",
    "docs/operations/NATIVE_INIT_WIFI_LIFECYCLE_COMMANDS.md",
    "docs/plans/A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md",
    "docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md",
    "docs/plans/A90_UFS_HANDOFF_ARCHITECTURE_AND_PRODUCTION_REDUCTION_PLAN_2026-08-12.md",
    "docs/reports/A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md",
    "docs/security/hardening/a90-debian-supervised-wlan-2026-08-15/proposals/debian-supervised-wlan.md",
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml",
    "workspace/public/src/native-init/a90_auto_handoff.c",
    "workspace/public/src/native-init/a90_server_distro.c",
    "workspace/public/src/native-init/a90_wificfg.c",
    "workspace/public/src/native-init/a90_wificfg.h",
    "workspace/public/src/native-init/v724/90_main.inc.c",
    "workspace/public/src/native-init/helpers/a90_android_execns_probe.c",
    "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py",
    "workspace/public/src/scripts/server-distro/a90_ondevice_evidence_v1.py",
    "workspace/public/src/scripts/server-distro/a90_h24_ufs_d1_runner_v1.py",
    "workspace/public/src/scripts/revalidation/a90_wifi_profile_stage.py",
    "workspace/public/src/scripts/revalidation/native_wifi_connect_carrier_handoff_v2174.py",
    "tests/test_a90_wifi_profile_stage.py",
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


class A90SdFreeInputEvidenceHardeningDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads((ANALYSIS / "hardening.json").read_text())
        self.proposal = (
            ANALYSIS / "proposals/typed-sd-free-input-evidence.md"
        ).read_text()
        self.flat_proposal = re.sub(r"\s+", " ", self.proposal)

    def test_evidence_collection_is_exact_and_current(self) -> None:
        self.assertEqual(len(EVIDENCE_RELS), 22)
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
            "credentialProvisionAuthorized",
            "deviceInstallAuthorized",
            "ufsMutationAuthorized",
            "sdRemovalAuthorized",
            "d0Authorized",
            "d1Authorized",
            "f1Authorized",
            "handoffAuthorized",
            "otherTargetsTouched",
        ):
            self.assertIs(authority[key], False)
        self.assertIn(
            "This is an H0 design decision only and changes no current contract or device state.",
            self.flat_proposal,
        )
        self.assertIn("No device, D0, D1, F1, candidate", self.proposal)

    def test_current_sources_prove_consumers_but_not_production_authority(self) -> None:
        wifi = (ROOT / "workspace/public/src/native-init/a90_wificfg.c").read_text()
        manifest = (
            ROOT
            / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml"
        ).read_text()
        helper = (
            ROOT / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
        ).read_text()
        stager = (
            ROOT
            / "workspace/public/src/scripts/revalidation/a90_wifi_profile_stage.py"
        ).read_text()
        transport = (
            ROOT
            / "workspace/public/src/scripts/revalidation/native_wifi_connect_carrier_handoff_v2174.py"
        ).read_text()
        contract = (ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md").read_text()

        self.assertIn('WIFICFG_PRIMARY_ROOT "/mnt/sdext/a90/config/wifi"', wifi)
        self.assertIn('WIFICFG_CACHE_ROOT "/cache/a90-wifi/config"', wifi)
        self.assertIn("/mnt/sdext/a90/private-property-v317", manifest)
        self.assertIn("/cache/a90-wifi-property-v2167", helper)
        self.assertIn('choices=("persistent", "cache")', stager)
        self.assertIn('tcpctl_run_line([TOYBOX, "mv", "-f", tmp_path, remote_path])', transport)
        self.assertIn("persistent settings, credentials, security state", contract)
        self.assertIn("consumer and prototype producer exist", self.proposal)
        self.assertIn("not an activated current A90 production capability", (
            ANALYSIS / "context.md"
        ).read_text())

    def test_typed_design_separates_all_sensitive_lifetimes(self) -> None:
        for phrase in (
            "Boot-public client key",
            "Persistent-private Wi-Fi generation",
            "Compatibility seed",
            "Native receipt and host join",
            "Per-boot server key",
        ):
            self.assertIn(phrase, self.proposal)
        self.assertIn("Debian has no path, mount, directory FD", self.flat_proposal)
        self.assertIn(
            "A full historical/private property snapshot is never accepted",
            self.flat_proposal,
        )
        self.assertIn("does not authorize the existing cache stager", self.proposal)
        self.assertFalse((ANALYSIS / "implementation").exists())

    def test_portfolio_has_three_options_and_recommends_typed_minimal(self) -> None:
        opportunity = self.data["opportunities"][0]
        self.assertEqual(opportunity["opportunityId"], "typed-sd-free-input-evidence")
        self.assertEqual(
            {option["optionId"] for option in opportunity["options"]},
            {
                "private-boot-bundle",
                "wholesale-cache-transplant",
                "typed-minimal-channels",
            },
        )
        self.assertEqual(opportunity["recommendedOptionId"], "typed-minimal-channels")
        self.assertIn("higher-precedence", opportunity["recommendation"])

    def test_every_option_has_tradeoffs_evidence_and_comparable_diagrams(self) -> None:
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
            self.assertTrue(option["residualRisks"])
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

    def test_sequence_keeps_sd_removal_after_resident_health(self) -> None:
        portfolio = (ANALYSIS / "hardening.md").read_text()
        flat_portfolio = re.sub(r"\s+", " ", portfolio)
        self.assertIn("Only then allocate and qualify a fresh successor", flat_portfolio)
        self.assertIn("exact resident health", flat_portfolio)
        self.assertIn("remove the SD card while attended", flat_portfolio)
        self.assertIn("no-SD D0", flat_portfolio)
        self.assertIn("Only after that proof", flat_portfolio)

    def test_secrets_and_property_overclaims_are_explicitly_rejected(self) -> None:
        self.assertIn("contains no Wi-Fi SSID/PSK", self.flat_proposal)
        self.assertIn("A full historical/private property snapshot is never accepted", self.proposal)
        self.assertIn("hardware encryption", self.proposal)
        self.assertIn("unproved", self.proposal)
        self.assertIn("native can observe its own process", self.flat_proposal)
        self.assertIn("It cannot authenticate its own SSH server from the outside", self.flat_proposal)

    def test_security_index_and_relative_links_resolve(self) -> None:
        security_index = (ROOT / "docs/security/README.md").read_text()
        self.assertIn("hardening/a90-sd-free-input-evidence-2026-08-15/", security_index)

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
