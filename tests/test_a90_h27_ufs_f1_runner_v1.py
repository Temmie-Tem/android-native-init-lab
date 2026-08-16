"""Hold the H27 F1 runner unqualified until real reviews exist.

This runner can flash the A90. It was authored by adapting the reviewed H24
runner, and the constants that matter most are not code the author gets to
choose: they restate findings an independent reviewer signed, which the runner
then cross-checks against that reviewer's report.

No such review exists for H27. These tests exist to keep that true and
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
RUNNER = SERVER / "a90_h27_ufs_f1_runner_v1.py"
H24_RUNNER = SERVER / "a90_h24_ufs_f1_runner_v1.py"
MANIFEST = REPO / (
    "workspace/public/src/scripts/revalidation/a90_flat_builder"
    "/versions/phase3-minimal-h27/manifest.toml"
)
RECEIPT = REPO / (
    "workspace/private/outputs"
    "/a90-h27-selfbuilt-kernel-ab-20260817-01/ab-receipt.json"
)
CANDIDATE = RECEIPT.parent / "A/boot.img"
RESIDENT = REPO / (
    "workspace/private/outputs"
    "/a90-h24-minimal-debian-dev-ab-20260812-01/A/boot.img"
)
HANDOFF = REPO / "docs/plans/A90_H27_INDEPENDENT_REVIEW_HANDOFF_2026-08-17.md"
RUNNER_TESTS = Path(__file__).resolve()


def load_h24():
    spec = importlib.util.spec_from_file_location("a90_h24_runner_ref", H24_RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["a90_h24_runner_ref"] = module
    spec.loader.exec_module(module)
    return module


def load_runner():
    spec = importlib.util.spec_from_file_location("a90_h27_runner_under_test", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["a90_h27_runner_under_test"] = module
    spec.loader.exec_module(module)
    return module


class H27RunnerUnqualifiedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_runner()
        cls.text = RUNNER.read_text(encoding="utf-8")

    def test_the_guard_names_exactly_the_review_bindings(self) -> None:
        """Only review artifacts remain unset; the predecessor is derivable."""
        with self.assertRaises(self.mod.ContractError) as caught:
            self.mod.require_h27_reviews_exist()
        message = str(caught.exception)
        self.assertIn("not qualified for any device effect", message)
        unset = sorted(message.split("bindings: ")[-1].split(", "))
        self.assertEqual(
            unset,
            [
                "EXECUTION_REVIEWER",
                "EXECUTION_REVIEW_INCIDENT",
                "EXECUTION_REVIEW_REQUIRED_INVARIANTS",
                "H27_REVIEW_DATE",
                "HOST_CAPABILITY_CLOSURE_SHA256",
                "HOST_CAPABILITY_INCIDENT",
                "HOST_CAPABILITY_REQUIRED_INVARIANTS",
                "HOST_CAPABILITY_REVIEWER",
            ],
        )

    def test_capability_validation_refuses_before_touching_the_filesystem(self) -> None:
        """The guard must fire ahead of the missing-file error, not behind it."""
        with self.assertRaises(self.mod.ContractError) as caught:
            self.mod.validate_host_capability_qualification()
        self.assertIn("not qualified for any device effect", str(caught.exception))

    def test_empty_invariants_are_not_a_permissive_default(self) -> None:
        self.assertEqual(self.mod.HOST_CAPABILITY_REQUIRED_INVARIANTS, ())
        self.assertEqual(self.mod.EXECUTION_REVIEW_REQUIRED_INVARIANTS, ())
        self.assertIn("must never read as", self.text)

    def test_the_h24_review_date_was_not_inherited(self) -> None:
        """A stale date would let an H24-dated report satisfy an H27 check."""
        self.assertEqual(
            self.mod.H27_REVIEW_DATE, "UNSET_PENDING_H27_CAPABILITY_REVIEW"
        )
        self.assertNotIn('"2026-08-12"', self.text)

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
        self.assertEqual(self.mod.CANDIDATE_VERSION, "0.11.194")
        self.assertEqual(
            self.mod.CANDIDATE_BUILD, "phase3-minimal-h27-selfbuilt-kernel-nocfp"
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
        self.assertIn("phase3-minimal-h27/manifest.toml", self.mod.VERSION_MANIFEST_REL)

    def test_the_fresh_state_paths_replace_the_h24_pair(self) -> None:
        """A90_TARGET_CONTRACT.md:320-324 -- a prior enable/latch pair is never reused."""
        self.assertEqual(
            self.mod.ENABLE_PATH,
            "/cache/a90-auto-handoff-phase3-minimal-h27.enable",
        )
        self.assertEqual(
            self.mod.LATCH_PATH, "/cache/a90-auto-handoff-phase3-minimal-h27.done"
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
            "workspace/public/src/scripts/server-distro/a90_h27_ufs_f1_runner_v1.py",
            self.mod.EXECUTION_SOURCE_RELS,
        )
        self.assertNotIn(
            "workspace/public/src/scripts/server-distro/a90_h24_ufs_f1_runner_v1.py",
            self.mod.EXECUTION_SOURCE_RELS,
        )

    def test_no_namespace_collides_with_the_h24_runner(self) -> None:
        """Two runners sharing a journal or approval space would break no-replay."""
        h24 = load_h24()
        for attr in (
            "SCHEMA",
            "RESULT_SCHEMA",
            "JOURNAL_SCHEMA",
            "QUALIFICATION_SCHEMA",
            "EXECUTION_REVIEW_SCHEMA",
            "INVENTORY_SCHEMA",
            "APPROVAL_SCHEMA",
            "APPROVAL_BINDING_SCHEMA",
            "APPROVAL_PREFIX",
            "CAPABILITY",
        ):
            self.assertNotEqual(
                getattr(self.mod, attr), getattr(h24, attr), attr
            )
        self.assertNotEqual(self.mod.RUN_ID_RE.pattern, h24.RUN_ID_RE.pattern)
        self.assertRegex("a90-h27-ufs-f1-20260817-01", self.mod.RUN_ID_RE)
        self.assertNotRegex("a90-h24-ufs-f1-20260817-01", self.mod.RUN_ID_RE)

    def test_the_journal_and_approval_paths_are_h27_specific(self) -> None:
        for token in ("h27-f1-live", "h27-f1-approval-prepared.json"):
            self.assertIn(token, self.text, token)
        for token in ('"h24-f1-live"', '"h24-f1-approval-prepared.json"'):
            self.assertNotIn(token, self.text, token)

    def test_the_terminal_status_is_h27_scoped(self) -> None:
        self.assertIn("PASS_A90_H27_UFS_RESIDENT_INSTALLED", self.text)

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


class H27ReviewHandoffTests(unittest.TestCase):
    """The handoff must match the runner, and must not pre-write the review."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_runner()
        cls.doc = HANDOFF.read_text(encoding="utf-8")

    def test_every_schema_it_promises_matches_the_runner(self) -> None:
        for value in (
            self.mod.CAPABILITY,
            self.mod.HOST_CAPABILITY_SCOPE,
            self.mod.EXECUTION_REVIEW_SCOPE,
            self.mod.EXECUTION_REVIEW_SCHEMA,
            self.mod.QUALIFICATION_SCHEMA,
            self.mod.HOST_REVIEW_REPORT_REL.split("/")[-1],
            self.mod.EXECUTION_REVIEW_REPORT_REL.split("/")[-1],
        ):
            self.assertIn(value, self.doc, value)

    def test_it_does_not_ask_the_reviewer_to_open_private_artifacts(self) -> None:
        """The runner requires workspace_private == 0; the handoff must agree.

        A handoff that asked for independent byte verification would only be
        satisfiable by a report the runner then rejects, so an honest reviewer
        could never pass and a passing report would be one that did not look.
        """
        self.assertIn("Do not open the private artifacts", self.doc)
        self.assertIn("named, not to be opened", self.doc)
        self.assertIn("`workspace_private: 0`", self.doc)
        self.assertIn("declarations to cross-check, not bytes to", self.doc)
        self.assertIn("Byte verification is delegated, not skipped", self.doc)
        for name in (
            "test_the_candidate_binding_matches_the_built_artifact",
            "test_the_bound_predecessor_evidence_matches_the_staged_run",
        ):
            self.assertIn(name, self.doc, name)
            self.assertIn(f"def {name}", RUNNER_TESTS.read_text(encoding="utf-8"), name)

    def test_the_declared_digests_agree_with_the_runner(self) -> None:
        for digest in (
            self.mod.CANDIDATE_BOOT_SHA256,
            self.mod.CURRENT_BOOT_SHA256,
            self.mod.CANDIDATE_MANIFEST_SHA256,
        ):
            self.assertIn(digest, self.doc, digest)

    def test_it_supplies_shape_but_not_findings(self) -> None:
        """A handoff that dictated the findings would defeat the review."""
        self.assertIn("It specifies **shape only**", self.doc)
        self.assertIn("does not supply findings", self.doc)
        self.assertIn("the reviewer's own words and judgement", self.doc)
        self.assertIn("**the reviewer's findings**", self.doc)

    def test_it_surfaces_the_security_reduction_to_the_reviewer(self) -> None:
        self.assertIn("real reduction in kernel exploit mitigation", self.doc)
        self.assertIn("should return no-go on the capability", self.doc)

    def test_it_discloses_the_prior_no_go_history(self) -> None:
        self.assertIn("no-go", self.doc)
        self.assertIn("three times", self.doc)
        self.assertIn("retired H25's identity", self.doc)
        self.assertIn("validated H18 as its starting resident", self.doc)

    def test_it_leaves_the_scoping_questions_open(self) -> None:
        for token in (
            "Predecessor terminal",
            "Proof axis semantics",
            "acceptable at all",
            "Terminal semantics",
        ):
            self.assertIn(token, self.doc, token)

    def test_it_says_a_pass_go_is_not_a_flash_authorization(self) -> None:
        self.assertIn("does not authorize a flash", self.doc)
        self.assertIn("it cannot grant authority", self.doc)


class H27RebindTests(unittest.TestCase):
    """The third no-go found a wrong identity and a wrong predecessor."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_runner()
        cls.text = RUNNER.read_text(encoding="utf-8")

    def test_the_retired_h25_identity_is_gone(self) -> None:
        self.assertEqual(self.mod.CANDIDATE_VERSION, "0.11.194")
        self.assertNotIn("0.11.193", self.text)
        goal = (REPO / "GOAL_A90.md").read_text(encoding="utf-8")
        self.assertIn("H25 `0.11.193`", goal)
        self.assertIn("NO_GO_RETIRED", goal)

    def test_the_predecessor_is_bound_to_the_actual_h24_resident(self) -> None:
        """Derived from H24's evidence, not from the H18 values it replaced."""
        self.assertEqual(self.mod.CURRENT_VERSION, "0.11.192")
        self.assertIn("phase3-minimal-h24-ufs-auth", self.mod.CURRENT_BUILD)
        self.assertEqual(self.mod.CURRENT_BOOT_SIZE, 58372096)
        self.assertFalse(hasattr(self.mod, "H18_D1_RECORDS"))
        self.assertNotIn("0.11.186", self.text)
        self.assertEqual(self.text.count("phase3-minimal-h18"), 1)  # provenance note only
        if not RESIDENT.is_file():
            self.skipTest(f"private artifact not staged on this host: {RESIDENT}")
        raw = RESIDENT.read_bytes()
        self.assertEqual(len(raw), self.mod.CURRENT_BOOT_SIZE)
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), self.mod.CURRENT_BOOT_SHA256
        )

    def test_the_predecessor_closure_digest_is_derived_not_invented(self) -> None:
        """It must equal H24's own execution qualification, as H18's did for H24."""
        import json

        h24 = json.loads(
            (
                REPO
                / "workspace/public/src/scripts/revalidation/a90_flat_builder"
                / "versions/phase3-minimal-h24/execution-qualification.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            self.mod.CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256,
            h24["execution_closure_sha256"],
        )
        h18 = json.loads(
            (
                REPO
                / "workspace/public/src/scripts/revalidation/a90_flat_builder"
                / "versions/phase3-minimal-h18/execution-qualification.json"
            ).read_text(encoding="utf-8")
        )
        h24_runner = (SERVER / "a90_h24_ufs_f1_runner_v1.py").read_text(encoding="utf-8")
        self.assertIn(h18["execution_closure_sha256"], h24_runner)

    def test_the_guard_no_longer_lists_the_bound_predecessor(self) -> None:
        """Filling the predecessor must shrink the guard, not silence it."""
        with self.assertRaises(self.mod.ContractError) as caught:
            self.mod.require_h27_reviews_exist()
        message = str(caught.exception)
        for name in (
            "CURRENT_VERSION",
            "CURRENT_BUILD",
            "CURRENT_BOOT_SHA256",
            "CURRENT_BOOT_SIZE",
            "CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256",
            "H24_D1_RECORDS",
        ):
            self.assertNotIn(name, message, name)

    def test_the_d1_scope_was_removed(self) -> None:
        for rel in self.mod.EXECUTION_SOURCE_RELS:
            self.assertNotIn("d1_runner", rel, rel)
            self.assertNotIn("persistent_server_observer", rel, rel)
        self.assertIn('or value.get("d1_runner_qualified") is not False', self.text)
        self.assertNotIn('or value.get("d1_runner_qualified") is not True', self.text)

    def test_the_proof_axis_comes_from_attribution_not_status(self) -> None:
        """Both FAILED terminals are raised from `except Exception` handlers that
        also catch host parse, timeout, and transfer-uncertainty defects, so a
        status lookup cannot tell a device contradiction from an observer defect.
        """
        self.assertEqual(self.mod.experiment_proof(self.mod.PASS_STATUS), "PROVED")
        for status in ("FAILED_INITIAL_HEALTH_ROLLED_BACK", "FAILED_CANDIDATE_ROLLED_BACK"):
            self.assertEqual(
                self.mod.experiment_proof(status), "NO_PROOF_OBSERVER", status
            )
            self.assertEqual(
                self.mod.experiment_proof(status, device_contradiction=True),
                "REFUTED",
                status,
            )
        with self.assertRaises(self.mod.ContractError):
            self.mod.experiment_proof(self.mod.PASS_STATUS, device_contradiction=True)
        self.assertNotIn("EXPERIMENT_PROOF_BY_STATUS", self.text)

    def test_a_consumer_refuses_a_mismatched_proof_axis(self) -> None:
        """A field nothing checks is decoration; this is the check."""
        bad = [
            {"status": self.mod.PASS_STATUS, "experiment_proof": "REFUTED",
             "device_safety_state": "RESIDENT_HEALTHY"},
            {"status": self.mod.PASS_STATUS, "experiment_proof": "NO_PROOF_OBSERVER",
             "device_safety_state": "RESIDENT_HEALTHY"},
            {"status": self.mod.PASS_STATUS, "experiment_proof": "PROVED",
             "device_safety_state": "BASELINE_HEALTHY"},
            {"status": "FAILED_CANDIDATE_ROLLED_BACK", "experiment_proof": "PROVED"},
            {"status": self.mod.PASS_STATUS, "device_safety_state": "RESIDENT_HEALTHY"},
        ]
        for result in bad:
            with self.assertRaises(self.mod.ContractError, msg=str(result)):
                self.mod.validate_experiment_proof(result)
        self.assertEqual(
            self.mod.validate_experiment_proof(
                {"status": self.mod.PASS_STATUS, "experiment_proof": "PROVED",
                 "device_safety_state": "RESIDENT_HEALTHY"}
            ),
            "PROVED",
        )

    def test_the_consumer_refuses_unattributed_refuted(self) -> None:
        """The three combinations the fourth review reproduced as fail-open.

        REFUTED burns an ordinal and forces a no-replay conclusion, so a
        tampered or corrupted durable result claiming it must be refused rather
        than trusted on the producer's discipline.
        """
        for status in (
            "FAILED_CANDIDATE_ROLLED_BACK",
            "FAILED_INITIAL_HEALTH_ROLLED_BACK",
            "FAILED_CANDIDATE_RECOVERY_ROLLBACK_COMPLETE",
        ):
            with self.assertRaises(self.mod.ContractError, msg=status) as caught:
                self.mod.validate_experiment_proof(
                    {"status": status, "experiment_proof": "REFUTED"}
                )
            self.assertIn("device-attribution receipt", str(caught.exception))

    def test_no_non_pass_status_accepts_anything_but_no_proof(self) -> None:
        """Total over every terminal this runner can emit, not a sample."""
        import re

        statuses = {
            status
            for status in re.findall(r'"status": "([A-Z_0-9]+)"', self.text)
            if status != self.mod.PASS_STATUS
            and status.startswith(("FAILED_", "ABORTED_"))
        }
        self.assertGreaterEqual(len(statuses), 5)
        for status in statuses:
            accepted = []
            for proof in ("PROVED", "REFUTED", "NO_PROOF_OBSERVER"):
                try:
                    self.mod.validate_experiment_proof(
                        {"status": status, "experiment_proof": proof}
                    )
                except self.mod.ContractError:
                    continue
                accepted.append(proof)
            self.assertEqual(accepted, ["NO_PROOF_OBSERVER"], status)

    def test_relaxing_refuted_requires_an_attribution_receipt(self) -> None:
        """Guard the comment so a later change cannot just delete the check."""
        self.assertIn("device-attribution receipt", self.text)
        self.assertIn("this must not simply relax", self.text)

    def test_the_durable_result_consumer_calls_the_validator(self) -> None:
        import inspect

        source = inspect.getsource(self.mod._validate_closed_result)
        self.assertIn("validate_experiment_proof(result)", source)

    def test_the_predecessor_is_h24_not_h18(self) -> None:
        self.assertEqual(
            self.mod.H24_F1_CLOSED_STATUS, "PASS_A90_H24_UFS_RESIDENT_INSTALLED"
        )
        self.assertIn("REFUTED_H24_", self.mod.H24_D1_CLOSED_STATUS)
        self.assertEqual(len(self.mod.H24_D1_RECORDS), 7)
        for name, size, sha in self.mod.H24_D1_RECORDS:
            self.assertTrue(name.endswith(".json"), name)
            self.assertGreater(size, 0, name)
            self.assertRegex(sha, r"^[0-9a-f]{64}$")
        self.assertNotIn("H18_D1_RECORDS", self.text)
        self.assertNotIn("A90_H18_POST_ROOT_FAILURE_ATTRIBUTION_V1", self.text)
        self.assertNotIn("PASS_A90_H18_UFS_RESIDENT_INSTALLED", self.text)
        self.assertTrue(hasattr(self.mod, "validate_h24_predecessor_terminal"))
        self.assertFalse(hasattr(self.mod, "validate_h18_d1_terminal"))

    def test_the_bound_predecessor_evidence_matches_the_staged_run(self) -> None:
        run = REPO / self.mod.H24_PREDECESSOR_RUN_REL
        if not run.is_dir():
            self.skipTest(f"private artifact not staged on this host: {run}")
        for rel, size, sha in (
            (self.mod.H24_F1_CLOSED_REL, self.mod.H24_F1_CLOSED_SIZE,
             self.mod.H24_F1_CLOSED_SHA256),
            (self.mod.H24_D1_CLOSED_REL, self.mod.H24_D1_CLOSED_SIZE,
             self.mod.H24_D1_CLOSED_SHA256),
        ):
            raw = (run / rel).read_bytes()
            self.assertEqual(len(raw), size, rel)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), sha, rel)
        d1 = run / "h24-d1/run01"
        for name, size, sha in self.mod.H24_D1_RECORDS:
            raw = (d1 / name).read_bytes()
            self.assertEqual(len(raw), size, name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), sha, name)

    def test_the_proof_axis_exists_and_is_total(self) -> None:
        """The design's third axis must be in the result, not only in prose."""
        import re

        emitted = {
            status
            for status in re.findall(r'"status": "([A-Z_0-9]+)"', self.text)
            if status.startswith(("PASS_A90", "FAILED_", "ABORTED_"))
        }
        self.assertTrue(emitted)
        for status in emitted:
            proof = self.mod.experiment_proof(status)
            self.assertIn(proof, ("PROVED", "NO_PROOF_OBSERVER"), status)

    def test_every_result_emission_carries_the_proof_axis(self) -> None:
        self.assertEqual(
            self.text.count('"schema": RESULT_SCHEMA'),
            self.text.count('"experiment_proof": experiment_proof('),
        )
