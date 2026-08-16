"""Pin the A90 self-built kernel F1 design draft.

A design draft is the document most likely to be mistaken for permission. It
names artifacts, a runner, and an acceptance predicate, which is exactly the
shape of an approval. These tests hold it as a draft, hold its stated
preconditions, and check the identities and the discriminator against the real
staged artifacts rather than against the draft's own prose.
"""

from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path
import unittest


def flatten(text: str) -> str:
    """Collapse wrapping and blockquote markers, as the sibling docs tests do."""
    return " ".join(text.replace("> ", " ").split())


REPO = Path(__file__).resolve().parents[1]
DESIGN = REPO / "docs/plans/A90_SELF_BUILT_KERNEL_F1_DESIGN_2026-08-16.md"
BUILD_REPORT = REPO / "docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md"
GOAL = REPO / "GOAL_A90.md"
PROCESS = REPO / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
RUNNER = REPO / "workspace/public/src/scripts/revalidation/native_init_flash.py"

BOOT_IMAGES = REPO / "workspace/private/inputs/boot_images"
KERNEL_INPUT = BOOT_IMAGES / "boot_a90_h24_selfbuilt_nocfp_20260816.img"
BASE_BOOT = BOOT_IMAGES / "boot_a90_base_selfbuilt_kernel_20260816.img"
CANDIDATE = REPO / (
    "workspace/private/outputs"
    "/a90-h24k-selfbuilt-kernel-ab-20260816-01/A/boot.img"
)
CANDIDATE_B = REPO / (
    "workspace/private/outputs"
    "/a90-h24k-selfbuilt-kernel-ab-20260816-01/B/boot.img"
)
ROLLBACK = BOOT_IMAGES / "boot_linux_v2321_usb_clean_identity_rodata.img"
RESIDENT = REPO / (
    "workspace/private/outputs"
    "/a90-h24-minimal-debian-dev-ab-20260812-01/A/boot.img"
)

DIGESTS = {
    "resident": "d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782",
    "candidate": "2c4ca81152987dc484d5b147f7a09a77f16f8fad0b7236cf3c67f4a562c6ceba",
    "rollback": "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb",
}
RUNNER_SHA = "366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53"
BANNER_RE = re.compile(rb"Linux version [0-9][^\x00]{0,220}")


def kernel_banner(boot_img: Path) -> str:
    """Extract the kernel version banner from a boot image's Image payload."""
    raw = boot_img.read_bytes()
    page = struct.unpack("<I", raw[36:40])[0]
    ksize = struct.unpack("<I", raw[8:12])[0]
    blob = raw[page : page + ksize]
    if blob[:16] == b"UNCOMPRESSED_IMG":
        size = struct.unpack("<I", blob[16:20])[0]
        blob = blob[20 : 20 + size]
    found = BANNER_RE.search(blob)
    if not found:
        raise ValueError(f"no kernel banner in {boot_img}")
    return found.group(0).decode("ascii", "replace")


class SelfBuiltKernelF1DesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = DESIGN.read_text(encoding="utf-8")
        self.design = flatten(self.raw)

    def test_it_is_marked_a_draft_that_grants_nothing(self) -> None:
        """The header must refuse to be read as permission."""
        head = flatten(self.raw[: self.raw.index("## The single question")])
        self.assertIn("DRAFT", head)
        self.assertIn("grants no authority", head)
        self.assertIn("is not an approval request", head)
        self.assertIn("Device or live effect of this document: none", head)
        self.assertIn("does not authorize that F1", head)

    def test_it_quotes_the_goal_that_currently_forbids_a_successor(self) -> None:
        quoted = "No successor candidate, approval, transfer, reboot, or D1 effect"
        self.assertIn(quoted, self.design)
        self.assertIn(quoted, flatten(GOAL.read_text(encoding="utf-8")))

    def test_the_scope_is_one_question_and_the_non_goals_are_listed(self) -> None:
        self.assertIn("Does the A90 boot a kernel this project compiled?", self.design)
        for token in (
            "It does not enable `CONFIG_ANDROID_BINDERFS`",
            "It does not change the device tree",
            "It does not retire any WLAN gate",
        ):
            self.assertIn(token, self.design, token)

    def test_the_cfp_acceptance_is_stated_before_the_identities(self) -> None:
        """A reviewer must meet the security cost before the artifact table."""
        accepted = self.raw.index("What is being accepted")
        identities = self.raw.index("## Identities")
        self.assertLess(accepted, identities)
        self.assertIn(
            "**Approving this F1 accepts a reduced kernel exploit-mitigation posture",
            self.raw,
        )
        self.assertIn("should reject this design rather than the artifact", self.design)

    def test_the_review_corrections_are_recorded_not_absorbed(self) -> None:
        """Draft 1 was returned no-go; the errors stay visible, not smoothed over."""
        self.assertIn("Supersedes draft 1", self.design)
        self.assertIn("returned **no-go**", self.raw)
        self.assertIn("What draft 1 got wrong", self.design)
        for token in (
            "The candidate identity was contract-violating",
            "The runner invocation did not exist",
            "The transaction owner was wrong",
            "Paths were relative",
            "The health predicate was incomplete",
            "Recovery was ambiguous",
            "First-use execution qualification was missing",
        ):
            self.assertIn(token, self.raw, token)
        self.assertIn(
            "One variable is a good instinct and it is not a licence to reuse an identity",
            self.design,
        )

    def test_the_candidate_was_built_with_a_new_identity(self) -> None:
        """The contract's core requirement, checked against the built artifact."""
        self.assertIn("Built on 2026-08-16", self.design)
        self.assertIn("`phase3-minimal-h24k`, version `0.11.193`", self.design)
        self.assertIn("qualification records are **still absent**", self.raw)
        if not (CANDIDATE.is_file() and CANDIDATE_B.is_file()):
            self.skipTest(f"private artifact not staged on this host: {CANDIDATE}")
        a = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
        b = hashlib.sha256(CANDIDATE_B.read_bytes()).hexdigest()
        self.assertEqual(a, b, "candidate A/B build is not reproducible")
        self.assertEqual(a, DIGESTS["candidate"])

    def test_the_candidate_carries_the_self_built_kernel(self) -> None:
        if not CANDIDATE.is_file():
            self.skipTest(f"private artifact not staged on this host: {CANDIDATE}")
        raw = CANDIDATE.read_bytes()
        page = struct.unpack("<I", raw[36:40])[0]
        blob = raw[page : page + struct.unpack("<I", raw[8:12])[0]]
        size = struct.unpack("<I", blob[16:20])[0]
        image = blob[20 : 20 + size]
        self.assertEqual(
            hashlib.sha256(image).hexdigest(),
            "6cab67938d2d235ad5ad965abaefe7e3ebda6d13b57251705c91f5f333ab1b6d",
        )
        self.assertNotIn("4.14.190-25818860", kernel_banner(CANDIDATE))

    def test_the_builder_base_boot_requirement_is_recorded(self) -> None:
        """An already-built image is rejected; the design must say why."""
        self.assertIn("base ramdisk already contains the H17 observer key path", self.design)
        self.assertIn("caps\n`extends` depth at 2", self.raw)
        if BASE_BOOT.is_file():
            self.assertEqual(
                hashlib.sha256(BASE_BOOT.read_bytes()).hexdigest(),
                "2d0be40158d56b6b053bc1aff6c6e149beb904da43a303b812e8ca6c4d583a9e",
            )

    def test_the_staged_image_is_declared_not_a_candidate(self) -> None:
        """The contract forbids reusing the resident's identity and latch paths."""
        self.assertIn("not itself a candidate", self.design)
        self.assertIn("not usable as a candidate", self.design)
        self.assertIn("Every replacement candidate uses a new build identity", self.design)
        self.assertIn("a prior enable/latch pair is never reused", self.design)
        self.assertIn("not itself a candidate", self.design)
        self.assertIn("then deleted", self.design)
        self.assertFalse(KERNEL_INPUT.exists(), "the dead-end image must not remain staged")

    def test_the_required_candidate_construction_is_specified(self) -> None:
        for token in (
            "`[inputs] base_boot`",
            "fresh `A90_AUTO_HANDOFF_ENABLE_PATH` and `A90_AUTO_HANDOFF_LATCH_PATH`",
            "deterministic A/B output",
            "capability-qualification.json",
            "execution-qualification.json",
        ):
            self.assertIn(token, self.design, token)

    def test_the_discriminator_reasoning_is_corrected(self) -> None:
        """With a new identity, --expect-version discriminates; /proc/version is extra."""
        self.assertIn("`--expect-version` discriminates candidate from rollback", self.design)
        self.assertIn("that requirement disappears with the correct construction", self.design)
        self.assertIn("supplementary", self.design)
        self.assertIn("not as the load-bearing discriminator", self.design)

    def test_refuted_is_allowed_as_a_real_terminal(self) -> None:
        self.assertIn("`REFUTED` is a legitimate answer to the single question", self.design)

    def test_every_precondition_is_listed_as_unmet(self) -> None:
        self.assertIn("none is satisfied by this document", self.design)
        for token in (
            "independent review of this draft",
            "a fresh connected D0",
            "exact attended F1 approval",
            "the operator physically present",
            "`--operator-attended` must never be asserted",
            "first-use execution qualification",
            "`A90_F1_RESIDENT_INSTALL_V1` binding",
            "an empty durable journal",
        ):
            self.assertIn(token, self.design, token)

    def test_the_rollback_never_waits_rule_is_exact(self) -> None:
        self.assertIn("**Once candidate execution begins, rollback never waits**", self.raw)
        self.assertIn("no second acknowledgement and no candidate retry", self.design)
        self.assertIn("closes only after V2321 health is verified", self.design)
        self.assertIn("`RECOVERY_REQUIRED`", self.design)
        self.assertIn("remains explicitly recovery-pending", self.design)

    def test_the_two_terminal_axes_are_separated(self) -> None:
        for token in (
            "RESIDENT_HEALTHY",
            "RECOVERY_REQUIRED",
            "PROVED",
            "REFUTED",
            "NO_PROOF_OBSERVER",
        ):
            self.assertIn(token, self.design, token)
        self.assertIn("Observation is not attribution", self.design)
        self.assertIn("not by a port answering", self.design)

    def test_target_isolation_is_bound(self) -> None:
        self.assertIn("Inventory all attached devices first", self.design)
        self.assertIn("S22+ and S20+ were untouched", self.design)
        self.assertIn("Serials and topology identifiers stay private", self.design)

    def test_the_orchestrator_owns_the_transaction_not_the_helper(self) -> None:
        self.assertIn("a90_v3403_f1_orchestrator.py", self.design)
        self.assertIn("the helper is not the transaction", self.design)
        self.assertIn("--verify-protocol selftest", self.design)
        self.assertIn("the boot image **positional**", self.design)
        transport = self.raw[self.raw.index("## Transport") : self.raw.index("## Acceptance predicate")]
        self.assertNotIn("--image", transport, "the nonexistent option must not reappear")

    def test_the_unavoidable_second_variable_is_disclosed(self) -> None:
        self.assertIn("Two things change at once, unavoidably", self.design)
        self.assertIn("it is not zero, and a boot failure", self.design)

    def test_the_open_risks_include_the_release_string_change(self) -> None:
        self.assertIn("**`uname -r` changes**", self.raw)
        self.assertIn("expected impact is low but not zero", self.design)
        self.assertIn("Functional equivalence is unproved", self.design)
        self.assertIn("Booting proves booting", self.design)
        self.assertIn("not evidence of equivalence", self.design)
        self.assertIn("CFP removal is not reversible by rebuilding", self.design)

    def test_the_one_variable_ordering_is_justified(self) -> None:
        self.assertIn("the failure would have two explanations", self.design)
        self.assertIn("one ambiguous bit", self.design)

    def test_the_recorded_digests_match_the_staged_artifacts(self) -> None:
        """The check that catches a design describing artifacts that moved."""
        for name, path in (
            ("resident", RESIDENT),
            ("candidate", CANDIDATE),
            ("rollback", ROLLBACK),
        ):
            self.assertIn(DIGESTS[name], self.raw, name)
            if not path.is_file():
                self.skipTest(f"private artifact not staged on this host: {path}")
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, DIGESTS[name], name)

    def test_the_runner_is_the_unchanged_one_the_design_names(self) -> None:
        self.assertTrue(RUNNER.is_file(), str(RUNNER))
        self.assertEqual(hashlib.sha256(RUNNER.read_bytes()).hexdigest(), RUNNER_SHA)
        self.assertIn(RUNNER_SHA, self.raw)
        self.assertIn("byte-identical to the helper used by the prior A90 F1 run", self.design)

    def test_the_quoted_banners_match_the_real_images(self) -> None:
        """The discriminator is only sound if both banners are what we claim."""
        for path in (CANDIDATE, RESIDENT):
            if not path.is_file():
                self.skipTest(f"private artifact not staged on this host: {path}")
        resident = kernel_banner(RESIDENT)
        candidate = kernel_banner(CANDIDATE)
        self.assertNotEqual(resident, candidate, "banners must differ to discriminate")
        self.assertIn("4.14.190-25818860-abA908NKSU5EWA3", resident)
        self.assertIn("4.14.190-25818860-abA908NKSU5EWA3", self.raw)
        self.assertIn("dpi@SWDK6110", self.raw)
        self.assertNotIn("4.14.190-25818860", candidate)
        self.assertIn("built by this project", self.raw)
        self.assertNotIn("temmie@debian", self.raw, "build host user must not be recorded")

    def test_the_candidate_differs_from_the_resident_in_kernel_size_only(self) -> None:
        for path in (CANDIDATE, RESIDENT):
            if not path.is_file():
                self.skipTest(f"private artifact not staged on this host: {path}")

        def header(path: Path) -> tuple[int, ...]:
            raw = path.read_bytes()[:1632]
            return struct.unpack("<10I", raw[8:48]) + (
                struct.unpack("<16s", raw[48:64])[0],
                raw[64:576],
            )

        new, ref = header(CANDIDATE), header(RESIDENT)
        differing = [i for i in range(len(ref)) if new[i] != ref[i]]
        self.assertEqual(differing, [0], "only kernel_size may differ")
        self.assertEqual(ref[0], 49827613)
        self.assertEqual(new[0], 49823517)

    def test_the_cited_companions_still_exist(self) -> None:
        for path in (BUILD_REPORT, GOAL, PROCESS):
            self.assertTrue(path.is_file(), str(path))

    def test_no_build_host_address_is_recorded(self) -> None:
        self.assertNotIn("192.168.", self.raw, "build host IP must not be recorded")


if __name__ == "__main__":
    unittest.main()
