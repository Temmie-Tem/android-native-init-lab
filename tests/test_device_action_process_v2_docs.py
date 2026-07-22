import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeviceActionProcessV2DocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        cls.goal = (ROOT / "GOAL.md").read_text(encoding="utf-8")
        cls.claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        cls.process = (
            ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"
        ).read_text(encoding="utf-8")
        cls.risk = (
            ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md"
        ).read_text(encoding="utf-8")
        cls.archived_agents = (
            ROOT / "docs/archive/policy/AGENTS_PRE_PROCESS_V2_2026-07-21.md"
        ).read_text(encoding="utf-8")
        cls.archived_goal = (
            ROOT / "docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md"
        ).read_text(encoding="utf-8")

    def test_active_contracts_remain_small(self):
        self.assertLessEqual(len(self.agents.splitlines()), 220)
        self.assertLessEqual(len(self.goal.splitlines()), 150)
        self.assertLessEqual(len(self.claude.splitlines()), 40)

    def test_no_candidate_policy_is_active(self):
        active_text = "\n".join((self.agents, self.goal, self.claude))
        self.assertNotIn("POLICY_STATE=ACTIVE", active_text)
        self.assertNotIn("BEGIN_S22PLUS", active_text)
        self.assertIn("No S22+ F1 live run is currently authorized", self.agents)
        self.assertIn(
            "No active S22+ F1 authorization", " ".join(self.goal.split())
        )

    def test_archives_are_explicitly_inert(self):
        self.assertIn("INERT HISTORICAL EVIDENCE", self.archived_agents[:600])
        self.assertIn("INERT HISTORICAL ROADMAP", self.archived_goal[:600])

    def test_process_v2_requires_regular_path_and_rollback_authority(self):
        combined = "\n".join((self.agents, self.process, self.risk))
        self.assertIn("ordinary regular files", combined)
        self.assertIn("Forbid `/proc/self/fd`", combined)
        self.assertIn("No second acknowledgement may block rollback", combined)
        self.assertIn("exactly one regular `boot.img.lz4` member", combined)

    def test_rollback_recovery_is_separate_and_cannot_retry_candidate(self):
        self.assertIn("This stops candidate experimentation", self.agents)
        self.assertIn("Only a separately invoked `recover` action", self.process)
        self.assertIn("does not retransmit automatically", self.process)
        self.assertIn("must never retry the candidate", self.agents)

    def test_process_v2_state_machine_is_canonical(self):
        for state in (
            "PREFLIGHT",
            "APPROVED",
            "DOWNLOAD_IDENTIFIED",
            "CANDIDATE_FLASHED",
            "OBSERVED",
            "RECOVERY_DOWNLOAD",
            "ROLLBACK_FLASHED",
            "HEALTH_VERIFIED",
            "CLOSED",
        ):
            self.assertIn(state, self.process)

    def test_frontier_advances_past_direct_pid1_without_live_authority(self):
        normalized_goal = " ".join(self.goal.split())
        normalized_agents = " ".join(self.agents.split())
        self.assertIn(
            "R4W1-D DIRECT PID1 PROVEN", normalized_goal
        )
        self.assertIn(
            "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK", self.goal
        )
        self.assertIn("P2.1-P2.16 complete/closed", self.goal)
        self.assertIn("P2.17-P2.20 complete, H0", self.goal)
        self.assertIn("P2.21-P2.23 complete/closed", self.goal)
        self.assertIn("P2.24-P2.25 complete, H0", self.goal)
        self.assertIn("P2.26 complete, H0", self.goal)
        self.assertIn("P2.27 complete, H0", self.goal)
        self.assertIn("P2.28 complete, D0", self.goal)
        self.assertIn("P2.29 gated, F1", self.goal)
        self.assertIn("The F1 binding is consumed", normalized_goal)
        self.assertIn("P2.1-P2.5 complete", self.process)
        self.assertIn("P2.6-P2.10 host path complete", self.process)
        self.assertIn("Typed Retained Evidence", self.process)
        self.assertIn("NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", self.process)
        self.assertIn("reusable D0/F1 adapters are complete", self.agents)
        self.assertIn("P2.28 passed connected read-only preparation", self.agents)
        self.assertIn(
            "Until then F1 is inactive", normalized_agents
        )
        self.assertIn(
            "PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY", self.process
        )
        self.assertIn("creates no F1 authority", self.process)
        self.assertIn(
            "GO_HOST_SOURCE_TO_SEPARATE_MANIFEST_READINESS_AND_D0_PREPARE",
            self.process,
        )
        self.assertIn("default manifest remains `draft-host-only`", self.process)
        self.assertIn("`ready-for-f1-approval` status", self.process)
        self.assertIn("private exact target binding", self.process)
        self.assertIn("aborted binding is not reusable", self.process)
        self.assertIn(
            "No active S22+ F1 authorization", " ".join(self.goal.split())
        )

    def test_archived_policy_is_not_runtime_dependency(self):
        self.assertIn(
            "Unreachable retired helpers and historical reports are not",
            self.process,
        )
        self.assertIn("Archived text is evidence only", self.goal)


if __name__ == "__main__":
    unittest.main()
