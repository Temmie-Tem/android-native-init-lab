"""Hold the H24K F1 runner unqualified until real reviews exist.

This runner can flash the A90. It was authored by adapting the reviewed H24
runner, and the constants that matter most are not code the author gets to
choose: they restate findings an independent reviewer signed, which the runner
then cross-checks against that reviewer's report.

No such review exists for H24K. These tests exist to keep that true and
visible: that the placeholders stay placeholders, that an empty invariant list
never reads as "nothing required", and that every device-effect entry point
refuses. A future change that fills the bindings must come with the report, and
these tests will demand it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "workspace/public/src/scripts/server-distro"
RUNNER = SERVER / "a90_h24k_ufs_f1_runner_v1.py"
H24_RUNNER = SERVER / "a90_h24_ufs_f1_runner_v1.py"
MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder"
    "/versions/phase3-minimal-h24k/manifest.toml"
)
RECEIPT = REPO / (
    "workspace/private/outputs"
    "/a90-h24k-selfbuilt-kernel-ab-20260816-01/ab-receipt.json"
)
CANDIDATE = RECEIPT.parent / "A/boot.img"


def load_runner():
    spec = importlib.util.spec_from_file_location("a90_h24k_runner_under_test", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["a90_h24k_runner_under_test"] = module
    spec.loader.exec_module(module)
    return module


class H24KRunnerUnqualifiedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_runner()
        cls.text = RUNNER.read_text(encoding="utf-8")

    def test_the_guard_refuses_and_names_every_unset_binding(self) -> None:
        with self.assertRaises(self.mod.ContractError) as caught:
            self.mod.require_h24k_reviews_exist()
        message = str(caught.exception)
        self.assertIn("not qualified for any device effect", message)
        for name in (
            "HOST_CAPABILITY_CLOSURE_SHA256",
            "HOST_CAPABILITY_REVIEWER",
            "HOST_CAPABILITY_INCIDENT",
            "HOST_CAPABILITY_REQUIRED_INVARIANTS",
            "EXECUTION_REVIEWER",
            "EXECUTION_REVIEW_INCIDENT",
            "EXECUTION_REVIEW_REQUIRED_INVARIANTS",
        ):
            self.assertIn(name, message, name)

    def test_capability_validation_refuses_before_touching_the_filesystem(self) -> None:
        """The guard must fire ahead of the missing-file error, not behind it."""
        with self.assertRaises(self.mod.ContractError) as caught:
            self.mod.validate_host_capability_qualification()
        self.assertIn("not qualified for any device effect", str(caught.exception))

    def test_empty_invariants_are_not_a_permissive_default(self) -> None:
        self.assertEqual(self.mod.HOST_CAPABILITY_REQUIRED_INVARIANTS, ())
        self.assertEqual(self.mod.EXECUTION_REVIEW_REQUIRED_INVARIANTS, ())
        self.assertIn("must never read as", self.text)

    def test_no_h24_review_binding_was_inherited(self) -> None:
        """The most dangerous edit would be quietly reusing H24's signed review."""
        for token in (
            "A90_H24_MINIMAL_DEBIAN_DEV_INDEPENDENT_REVIEW_2026-08-12.json",
            "A90_H24_UFS_F1_D1_EXECUTION_INDEPENDENT_REVIEW_2026-08-12.json",
            "/root/a90_h23_dev_isolation_review/",
            "c1fbf02e266ba59f8ba72c5b1be95e302384beedb129ce0eb7c3125c1657d587",
        ):
            self.assertNotIn(token, self.text, token)

    def test_the_reviews_it_names_really_are_absent(self) -> None:
        for rel in (
            self.mod.HOST_REVIEW_REPORT_REL,
            self.mod.EXECUTION_REVIEW_REPORT_REL,
            self.mod.HOST_QUALIFICATION_REL,
        ):
            self.assertFalse(
                (REPO / rel).exists(),
                f"{rel} exists; if a real review was added, fill the bindings too",
            )

    def test_the_candidate_binding_matches_the_built_artifact(self) -> None:
        self.assertEqual(self.mod.CANDIDATE_VERSION, "0.11.193")
        self.assertEqual(
            self.mod.CANDIDATE_BUILD, "phase3-minimal-h24k-selfbuilt-kernel-nocfp"
        )
        if not CANDIDATE.is_file():
            self.skipTest(f"private artifact not staged on this host: {CANDIDATE}")
        raw = CANDIDATE.read_bytes()
        self.assertEqual(len(raw), self.mod.CANDIDATE_BOOT_SIZE)
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), self.mod.CANDIDATE_BOOT_SHA256
        )

    def test_the_receipt_binding_matches(self) -> None:
        if not RECEIPT.is_file():
            self.skipTest(f"private artifact not staged on this host: {RECEIPT}")
        raw = RECEIPT.read_bytes()
        self.assertEqual(len(raw), self.mod.CANDIDATE_AB_RECEIPT_SIZE)
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), self.mod.CANDIDATE_AB_RECEIPT_SHA256
        )
        receipt = json.loads(raw.decode("utf-8"))
        artifacts = receipt["artifacts"]
        self.assertEqual(artifacts["init"]["sha256"], self.mod.CANDIDATE_INIT_SHA256)
        self.assertEqual(
            artifacts["ramdisk"]["sha256"], self.mod.CANDIDATE_RAMDISK_SHA256
        )
        self.assertEqual(artifacts["boot"]["sha256"], self.mod.CANDIDATE_BOOT_SHA256)

    def test_the_manifest_binding_matches(self) -> None:
        self.assertTrue(MANIFEST.is_file(), str(MANIFEST))
        self.assertEqual(
            hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            self.mod.CANDIDATE_MANIFEST_SHA256,
        )
        self.assertIn("phase3-minimal-h24k/manifest.toml", self.mod.VERSION_MANIFEST_REL)

    def test_the_fresh_state_paths_replace_the_h24_pair(self) -> None:
        """A90_TARGET_CONTRACT.md:320-324 -- a prior enable/latch pair is never reused."""
        self.assertEqual(
            self.mod.ENABLE_PATH,
            "/cache/a90-auto-handoff-phase3-minimal-h24k.enable",
        )
        self.assertEqual(
            self.mod.LATCH_PATH, "/cache/a90-auto-handoff-phase3-minimal-h24k.done"
        )
        self.assertEqual(
            self.mod.FORBIDDEN_PRIOR_STATE_PATHS,
            (
                "/cache/a90-auto-handoff-phase3-minimal-h24.enable",
                "/cache/a90-auto-handoff-phase3-minimal-h24.done",
            ),
        )

    def test_the_self_built_kernel_and_its_posture_are_pinned(self) -> None:
        self.assertEqual(
            self.mod.CANDIDATE_KERNEL_IMAGE_SHA256,
            "6cab67938d2d235ad5ad965abaefe7e3ebda6d13b57251705c91f5f333ab1b6d",
        )
        self.assertIs(self.mod.CANDIDATE_KERNEL_RKP_CFP_DISABLED, True)

    def test_it_binds_its_own_source_not_the_h24_runner(self) -> None:
        self.assertIn(
            "workspace/public/src/scripts/server-distro/a90_h24k_ufs_f1_runner_v1.py",
            self.mod.EXECUTION_SOURCE_RELS,
        )
        self.assertNotIn(
            "workspace/public/src/scripts/server-distro/a90_h24_ufs_f1_runner_v1.py",
            self.mod.EXECUTION_SOURCE_RELS,
        )

    def test_the_h24_runner_was_not_modified(self) -> None:
        """Adapting H24 must not disturb the resident's own qualified runner."""
        self.assertTrue(H24_RUNNER.is_file(), str(H24_RUNNER))
        h24 = H24_RUNNER.read_text(encoding="utf-8")
        self.assertIn('CANDIDATE_VERSION = "0.11.192"', h24)
        self.assertIn(
            "docs/reports/A90_H24_MINIMAL_DEBIAN_DEV_INDEPENDENT_REVIEW_2026-08-12.json",
            h24,
        )


if __name__ == "__main__":
    unittest.main()
