"""Pin the boot-only F1 owner design, especially the rule that breaks the loop.

Six reviews of the per-candidate runner each found real defects, and the cause
was structural: review findings were stored as code constants, so recording a
review changed the thing it reviewed. This design separates them. These tests
hold that separation, hold the hardcoded limits a manifest must never be able
to express, and hold the hazard binding at all three points -- because this
session twice shipped a field that nothing enforced.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import unittest


def flatten(text: str) -> str:
    """Collapse wrapping and blockquote markers, as the sibling docs tests do."""
    return " ".join(text.replace("> ", " ").split())


REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / "docs/plans/A90_BOOT_ONLY_F1_OWNER_V1_DESIGN_2026-08-17.md"
SERVER = REPO / "workspace/public/src/scripts/server-distro"
FLASH = REPO / "workspace/public/src/scripts/revalidation/native_init_flash.py"
ORCHESTRATOR = SERVER / "a90_v3403_f1_orchestrator.py"
GOAL = REPO / "GOAL_A90.md"

FLASH_SHA = "366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53"
RETIRED = (
    "a90_h15_ufs_f1_runner_v1.py",
    "a90_h15_ufs_d1_runner_v1.py",
    "a90_h16_ufs_f1_runner_v1.py",
    "a90_h16_ufs_d1_runner_v1.py",
    "a90_h17_ufs_f1_runner_v1.py",
    "a90_h17_ufs_d1_runner_v1.py",
    "a90_h18_ufs_f1_runner_v1.py",
    "a90_h18_ufs_d1_runner_v1.py",
    "a90_h24_ufs_f1_runner_v1.py",
    "a90_h24_ufs_d1_runner_v1.py",
    "a90_h27_ufs_f1_runner_v1.py",
)


class BootOnlyF1OwnerDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = DESIGN.read_text(encoding="utf-8")
        self.design = flatten(self.raw)

    def test_it_is_a_structural_draft_that_authorizes_nothing(self) -> None:
        head = flatten(self.raw[: self.raw.index("## The loop being removed")])
        self.assertIn("DRAFT", head)
        self.assertIn("grants no authority", head)
        self.assertIn("implements nothing", head)
        self.assertIn("Device or live effect of this document: none", head)

    def test_the_cycle_breaking_rule_is_stated_as_a_rule(self) -> None:
        """This is the whole point; it must not read as a nice-to-have."""
        self.assertIn(
            "**Review artifacts sign the owner closure. The owner closure never contains\nreview artifacts.**",
            self.raw,
        )
        self.assertIn("producing it cannot change what it signed", self.design)
        self.assertIn("There is no fixed point", self.design)

    def test_both_causes_of_the_loop_are_named(self) -> None:
        self.assertIn("Self-reference", self.design)
        self.assertIn("Lineage drag", self.design)
        self.assertIn("32 places", self.design)
        self.assertIn("colliding journal namespaces", self.design)

    def test_the_two_review_layers_separate_code_from_data(self) -> None:
        self.assertIn("only when owner code changes", self.design)
        self.assertIn("every candidate", self.design)
        self.assertIn("they do not re-open the owner capability review", self.design)

    def test_the_manifest_cannot_express_authority(self) -> None:
        for token in (
            "the `boot` partition as the only writable target",
            "exactly one candidate attempt",
            "exactly one rollback attempt",
            "cannot name a command, a partition, or a retry count",
        ):
            self.assertIn(token, self.design, token)
        self.assertIn("`--boot-block` and `--remote-image` at their defaults", self.design)

    def test_preflight_separates_healthy_from_expected(self) -> None:
        """Conflating them is how an H18 predecessor survived in an H27 runner."""
        self.assertIn("the device is healthy", self.design)
        self.assertIn("is the resident this manifest expects", self.design)
        self.assertIn("stops before any effect", self.design)

    def test_runtime_rehash_replaces_delegated_verification(self) -> None:
        self.assertIn("at execution time", self.design)
        self.assertIn("That is the authoritative check", self.design)
        self.assertIn("No reviewer reads private bytes", self.design)
        self.assertIn("no receipt needs binding", self.design)

    def test_the_hazard_is_bound_at_three_points(self) -> None:
        """A field nothing enforces is decoration; this session shipped two."""
        self.assertIn("RKP_CFP_DISABLED_RESIDENT", self.design)
        self.assertIn("binds it by digest", self.design)
        self.assertIn("over the manifest SHA **and** the hazard ID", self.design)
        self.assertIn("`accepted: true`", self.design)
        self.assertIn("unknown or unqualified hazard ID stops the owner", self.design)
        self.assertIn("empty invariant tuple", self.design)

    def test_the_state_machine_has_three_terminals_and_no_refuted(self) -> None:
        for state in (
            "PREPARED",
            "APPROVED",
            "CANDIDATE_INTENT",
            "PASS_A90_H27_RESIDENT_INSTALLED",
            "NO_PROOF_ROLLED_BACK",
            "RECOVERY_REQUIRED",
        ):
            self.assertIn(state, self.raw, state)
        self.assertIn("There is no `REFUTED`", self.design)
        self.assertIn("does not adjudicate why a kernel failed to boot", self.design)

    def test_the_closure_excludes_the_orchestrator(self) -> None:
        self.assertIn("must not import `a90_v3403_f1_orchestrator.py`", self.design)
        self.assertIn("closure constraint, not a\nstyle preference", self.raw)
        self.assertTrue(ORCHESTRATOR.is_file(), str(ORCHESTRATOR))

    def test_the_pinned_flash_helper_digest_is_real(self) -> None:
        self.assertIn(FLASH_SHA, self.raw)
        self.assertTrue(FLASH.is_file(), str(FLASH))
        self.assertEqual(hashlib.sha256(FLASH.read_bytes()).hexdigest(), FLASH_SHA)

    def test_every_named_retired_runner_exists_and_is_listed(self) -> None:
        for name in RETIRED:
            self.assertIn(name, self.raw, name)
            self.assertTrue((SERVER / name).is_file(), name)
        self.assertIn("must not execute a new candidate", self.design)
        self.assertIn("A90-H15-F1-APPROVE:", self.design)
        self.assertIn("`h15-f1-live`", self.design)

    def test_the_hostile_corpus_covers_the_defects_reviews_found(self) -> None:
        """Each entry here maps to a real failure, not a hypothetical."""
        for token in (
            "non-`boot` partition",
            "more than one candidate or rollback attempt",
            "resident other than `expected_start`",
            "runtime hash differs from the manifest",
            "approval token that does not derive from this manifest SHA",
            "missing the hazard ID",
            "crash after `CANDIDATE_INTENT`",
            "without\n  candidate replay",
            "colliding with a retired runner's namespace",
        ):
            self.assertIn(token, self.raw, token)

    def test_it_does_not_overclaim_what_it_saves(self) -> None:
        self.assertIn("does not remove the one-time cost", self.design)
        self.assertIn("needs a full capability review before first use", self.design)
        self.assertIn("It does not implement the owner", self.design)
        self.assertIn("It does not authorize an F1", self.design)

    def test_the_goal_still_forbids_a_successor(self) -> None:
        quoted = "No successor candidate, approval, transfer, reboot, or D1 effect"
        self.assertIn(quoted, flatten(GOAL.read_text(encoding="utf-8")))
        self.assertIn("no successor candidate, transfer, or reboot is authorized", self.design)

    def test_the_h27_work_is_declared_carried_forward(self) -> None:
        self.assertIn("retired before ever executing", self.design)
        self.assertIn("phase3-minimal-h27", self.design)
        self.assertIn("are unaffected and carry forward", self.design)


if __name__ == "__main__":
    unittest.main()
