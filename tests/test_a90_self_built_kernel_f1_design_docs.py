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
CANDIDATE = BOOT_IMAGES / "boot_a90_h24_selfbuilt_nocfp_20260816.img"
ROLLBACK = BOOT_IMAGES / "boot_linux_v2321_usb_clean_identity_rodata.img"
RESIDENT = REPO / (
    "workspace/private/outputs"
    "/a90-h24-minimal-debian-dev-ab-20260812-01/A/boot.img"
)

DIGESTS = {
    "resident": "d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782",
    "candidate": "7c293af9c0fd6bfea5247cd5c3415956c452c67a79e8269c967860d2a2c0cead",
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
            "It does not change userspace",
            "It does not change the device tree",
            "It does not retire any WLAN gate",
        ):
            self.assertIn(token, self.design, token)

    def test_the_cfp_acceptance_is_stated_before_the_identities(self) -> None:
        """A reviewer must meet the security cost before the artifact table."""
        accepted = self.raw.index("What is being accepted")
        identities = self.raw.index("## Exact identities")
        self.assertLess(accepted, identities)
        self.assertIn(
            "**Approving this F1 accepts a reduced kernel exploit-mitigation posture",
            self.raw,
        )
        self.assertIn("should reject this design rather than the artifact", self.design)

    def test_the_discriminator_problem_is_named_not_glossed(self) -> None:
        """Same ramdisk means the usual version check would pass on a fallback."""
        self.assertIn(
            "**A version check cannot tell the candidate from the rollback here.**",
            self.raw,
        )
        self.assertIn("would pass on a silent fallback", self.design)
        self.assertIn("`/proc/version` matches the pinned candidate banner", self.design)
        self.assertIn("Condition 3 is what makes this experiment mean anything", self.design)

    def test_the_dangerous_stop_condition_is_present(self) -> None:
        self.assertIn("this is the dangerous case", self.design)
        self.assertIn("something booted and it is not what we flashed", self.design)

    def test_refuted_is_allowed_as_a_real_terminal(self) -> None:
        self.assertIn("`REFUTED` is a legitimate terminal", self.design)

    def test_every_precondition_is_listed_as_unmet(self) -> None:
        self.assertIn("none is satisfied by this document", self.design)
        for token in (
            "independent review of this design",
            "a fresh connected D0 qualification",
            "exact attended F1 approval",
            "the operator physically present",
            "`--operator-attended` must never be asserted",
        ):
            self.assertIn(token, self.design, token)

    def test_the_open_risks_include_the_release_string_change(self) -> None:
        self.assertIn("**`uname -r` changes**", self.raw)
        self.assertIn("It is not zero", self.design)
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
        self.assertIn("byte-identical to the runner used by the prior A90 F1 run", self.design)

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
        self.assertIn("temmie@debian", candidate)
        self.assertIn("temmie@debian", self.raw)
        self.assertNotIn("4.14.190-25818860", candidate)

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
