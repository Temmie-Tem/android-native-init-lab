from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "workspace/public/src/scripts/server-distro/a90_resident_promotion_v1_model.py"
)
POLICY = REPO_ROOT / "docs/operations/A90_RESIDENT_BOOT_PROMOTION_V1.md"
AGENTS = REPO_ROOT / "AGENTS.md"
PROCESS = REPO_ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
TIERS = REPO_ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md"


def load_module():
    spec = importlib.util.spec_from_file_location("a90_resident_promotion_v1_model", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ResidentPromotionV1ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = load_module()

    def test_success_closes_promoted_without_rollback(self) -> None:
        result = self.model.simulate("success")
        self.assertEqual(result["terminal_state"], "PROMOTED_CLOSED")
        self.assertEqual(result["counts"]["candidate_attempts"], 1)
        self.assertEqual(result["counts"]["rootfs_stage_attempts"], 1)
        self.assertEqual(result["counts"]["candidate_flashes"], 1)
        self.assertEqual(result["counts"]["candidate_health_checks"], 2)
        self.assertEqual(result["counts"]["resident_reboots"], 1)
        self.assertEqual(result["counts"]["rollback_attempts"], 0)
        self.assertTrue(result["usb_generations_distinct"])
        self.assertFalse(result["device_action"])
        self.assertFalse(result["live_authority"])

    def test_exact_existing_rootfs_rejoins_without_staging_write(self) -> None:
        result = self.model.simulate("existing-rootfs-success")
        self.assertEqual(result["terminal_state"], "PROMOTED_CLOSED")
        self.assertEqual(result["rootfs_source_mode"], "verified-existing")
        self.assertEqual(result["counts"]["rootfs_stage_attempts"], 0)
        self.assertEqual(result["counts"]["candidate_attempts"], 1)

    def test_definite_pre_session_failures_abort_without_rollback(self) -> None:
        for scenario in (
            "preflight-failure",
            "rootfs-stage-failure",
            "rootfs-stage-failure-exact",
            "post-stage-pre-candidate-rejection",
            "candidate-local-parse-failure",
        ):
            with self.subTest(scenario=scenario):
                result = self.model.simulate(scenario)
                self.assertEqual(result["terminal_state"], "ABORTED")
                self.assertEqual(result["counts"]["candidate_attempts"], 0)
                self.assertEqual(result["counts"]["rollback_attempts"], 0)
                self.assertIsNotNone(result["abort_reason"])

    def test_every_post_attempt_failure_rolls_back_once(self) -> None:
        for scenario in (
            "candidate-transfer-ambiguous",
            "candidate-health-failure",
            "resident-reboot-ambiguous",
            "resident-health-failure",
        ):
            with self.subTest(scenario=scenario):
                result = self.model.simulate(scenario)
                self.assertEqual(result["terminal_state"], "ROLLED_BACK_CLOSED")
                self.assertEqual(result["counts"]["candidate_attempts"], 1)
                self.assertEqual(result["counts"]["rollback_attempts"], 1)
                self.assertEqual(result["counts"]["rollback_flashes"], 1)
                self.assertEqual(result["counts"]["rollback_health_checks"], 1)

    def test_ambiguous_rootfs_stage_blocks_before_candidate(self) -> None:
        result = self.model.simulate("rootfs-stage-ambiguous")
        self.assertEqual(result["terminal_state"], "BLOCKED")
        self.assertEqual(result["counts"]["candidate_attempts"], 0)
        self.assertEqual(result["counts"]["rootfs_stage_attempts"], 1)
        self.assertEqual(result["counts"]["rollback_attempts"], 0)
        self.assertIn("ROOTFS_STAGE_INTENT", result["history"])
        self.assertFalse(result["rootfs_safe_closure"])

    def test_staging_abort_requires_exact_safe_closure(self) -> None:
        model = self.model.PromotionModel()
        model.classify_rootfs("absent")
        model.approve()
        model.rootfs_stage_intent()
        with self.assertRaisesRegex(
            self.model.ContractError,
            "staging abort requires exact-or-absent safe closure",
        ):
            model.abort_before_attempt("rootfs-safe-failure")

    def test_candidate_intent_cannot_abort_with_ambiguous_reason(self) -> None:
        model = self.model.PromotionModel()
        model.classify_rootfs("absent")
        model.approve()
        model.rootfs_stage_intent()
        model.complete_rootfs_stage()
        model.mark_rootfs_ready()
        model.candidate_intent()
        with self.assertRaisesRegex(
            self.model.ContractError,
            "abort reason is not exact",
        ):
            model.abort_before_attempt("candidate-transport-ambiguous")

    def test_same_usb_generation_cannot_close_resident_health(self) -> None:
        model = self.model.PromotionModel()
        model.classify_rootfs("absent")
        model.approve()
        model.rootfs_stage_intent()
        model.complete_rootfs_stage()
        model.mark_rootfs_ready()
        model.candidate_intent()
        model.candidate_attempt_started()
        model.candidate_flashed()
        model.candidate_health_verified("same-generation")
        model.resident_reboot_intent()
        model.resident_rebooted()
        with self.assertRaisesRegex(
            self.model.ContractError,
            "must differ from candidate",
        ):
            model.resident_health_verified("same-generation")

    def test_rollback_failure_stops_in_recovery_required(self) -> None:
        result = self.model.simulate("rollback-failure")
        self.assertEqual(result["terminal_state"], "RECOVERY_REQUIRED")
        self.assertEqual(result["counts"]["rollback_attempts"], 1)
        self.assertEqual(result["counts"]["rollback_flashes"], 0)

    def test_invalid_shortcut_to_promoted_is_rejected(self) -> None:
        model = self.model.PromotionModel()
        with self.assertRaisesRegex(self.model.ContractError, "invalid promotion transition"):
            model.move(self.model.State.PROMOTED_CLOSED)

    def test_source_is_pure_h0(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import socket",
            "import subprocess",
            "import a90ctl",
            "native_init_flash",
            "--execute",
            "--approval",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('"device_action": False', source)
        self.assertIn('"live_authority": False', source)

    def test_policy_is_target_specific_and_non_authorizing(self) -> None:
        policy = POLICY.read_text(encoding="utf-8")
        compact = " ".join(policy.split())
        self.assertIn("A90 only", policy)
        self.assertIn(
            "H0_RUNNER_REVIEWED_NO_LIVE_MANIFEST",
            policy,
        )
        self.assertIn("PASS_A90_F1_RP_RESIDENT_PROMOTED", policy)
        self.assertIn("NO_PROOF_A90_F1_RP_CANDIDATE_ROLLED_BACK", policy)
        self.assertIn("does not grant live authority", compact)
        self.assertIn("S22+", policy)
        self.assertIn(
            "After `PROMOTED_CLOSED`, `ROLLED_BACK_CLOSED`, `ABORTED`, or `BLOCKED`",
            policy,
        )
        self.assertIn(
            "transaction retains only the exact rollback recovery authority",
            compact,
        )
        self.assertIn("authorizes at most one absent-only rootfs staging attempt", compact)
        self.assertIn("classified `exact` takes a read-only verified-existing path", compact)
        self.assertIn("ROOTFS_EXISTING_VERIFIED", policy)
        self.assertIn("ROOTFS_READY", policy)
        self.assertIn("it is not deleted or restaged", compact)

    def test_binding_docs_preserve_ordinary_f1_and_isolate_a90(self) -> None:
        agents = AGENTS.read_text(encoding="utf-8")
        process = PROCESS.read_text(encoding="utf-8")
        tiers = TIERS.read_text(encoding="utf-8")
        self.assertIn(
            "ordinary Process v2 is one boot-only candidate transfer plus its\n"
            "  mandatory rollback",
            agents,
        )
        self.assertIn(
            "A90 resident boot-promotion v1 has an independently reviewed H0 runner",
            agents,
        )
        process_compact = " ".join(process.split())
        self.assertIn("does not alter the ordinary state machine", process_compact)
        self.assertIn("or any S22+ run", process_compact)
        self.assertIn("A90 alone has a target-specific resident-promotion", tiers)
        self.assertIn("This does not apply to S22+", tiers)


if __name__ == "__main__":
    unittest.main()
