import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS_REVIEW_THRESHOLD_LINES = 220
AGENTS_HARD_MAX_LINES = 260
GOAL_REVIEW_THRESHOLD_LINES = 800
GOAL_HARD_MAX_LINES = 900
ATTENDED_REQUIRED_CLAUSES = (
    "Status: `H0_DESIGN_SELECTED_IMPLEMENTATION_REQUIRED`",
    "It is not live authority and cannot be applied to a candidate after candidate intent.",
    '"attended_window_sec": 900',
    '"pre_handoff_attempt_limit": 3',
    '"handoff_attempt_limit": 1',
    "The F1 approval binding must include all four values.",
    "Version 1 accepts no window above 900 seconds, no pre-handoff budget above three, and no handoff limit other than one.",
    "no handoff intent was recorded;",
    "the handoff command was not sent;",
    "Expiry, attempt exhaustion, target ambiguity, health mismatch, lost recovery, or an unclassified error closes continuation authority. Only rollback recovery may follow.",
    "the runner durably commits `attended-handoff-started` and fsyncs its journal record before dispatching the first byte",
    "After that durable intent, observation and rollback form a one-way path; no health, channel, or handoff command may be retried.",
    "This standing treatment does not cover reboot, Download/recovery entry, service start or stop, mount, network reconfiguration, file mutation, payload transfer, or any action that can remove the recovery path.",
    "Rollback must not wait for an attended-continuation acknowledgement and must never repeat the candidate.",
    "This contract cannot reactivate, extend, or reinterpret a consumed or failed run.",
)


def normalized(text):
    return " ".join(text.split())


def attended_contract_issues(text):
    value = normalized(text)
    return tuple(
        clause for clause in ATTENDED_REQUIRED_CLAUSES if clause not in value
    )


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
        cls.a90_attended = (
            ROOT / "docs/operations/A90_F1_ATTENDED_OBSERVATION_V1.md"
        ).read_text(encoding="utf-8")
        cls.p280_resume_femto_audit = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P280_RESUME_FEMTO_EUD_"
            "INSTRUMENTATION_AUDIT_H0_2026-07-28.md"
        ).read_text(encoding="utf-8")
        cls.archived_agents = (
            ROOT / "docs/archive/policy/AGENTS_PRE_PROCESS_V2_2026-07-21.md"
        ).read_text(encoding="utf-8")
        cls.archived_goal = (
            ROOT / "docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md"
        ).read_text(encoding="utf-8")

    def test_active_contracts_remain_small(self):
        self.assertLessEqual(
            len(self.agents.splitlines()),
            AGENTS_HARD_MAX_LINES,
            (
                "AGENTS.md exceeds its hard limit; review completed posture "
                f"for archival after {AGENTS_REVIEW_THRESHOLD_LINES} lines"
            ),
        )
        self.assertLessEqual(
            len(self.goal.splitlines()),
            GOAL_HARD_MAX_LINES,
            (
                "GOAL.md exceeds its hard limit; review completed history for "
                f"archival after {GOAL_REVIEW_THRESHOLD_LINES} lines"
            ),
        )
        self.assertLessEqual(len(self.claude.splitlines()), 40)

    def test_no_candidate_policy_is_active(self):
        active_text = "\n".join((self.agents, self.goal, self.claude))
        self.assertNotIn("POLICY_STATE=ACTIVE", active_text)
        self.assertNotIn("BEGIN_S22PLUS", active_text)
        self.assertIn("No S22+ F1 live run is currently authorized", self.agents)
        self.assertIn(
            "No S22+ F1 live run is currently authorized",
            " ".join(self.goal.split()),
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

    def test_a90_attended_mode_is_predeclared_bounded_and_nonretroactive(self):
        combined = "\n".join(
            (self.agents, self.process, self.risk, self.a90_attended)
        )
        for token in (
            "operator-attended-v1",
            "attended_window_sec",
            "pre_handoff_attempt_limit",
            "handoff_attempt_limit",
            "attended-window-open",
            "attended-handoff-started",
            "cannot be added after candidate intent",
            "must never retry the candidate",
        ):
            self.assertIn(token, combined)
        self.assertEqual(attended_contract_issues(self.a90_attended), ())

    def test_a90_attended_contract_rejects_each_load_bearing_mutation(self):
        source = normalized(self.a90_attended)
        for index, clause in enumerate(ATTENDED_REQUIRED_CLAUSES):
            with self.subTest(clause=clause):
                mutated = source.replace(clause, f"removed-clause-{index}", 1)
                self.assertIn(clause, attended_contract_issues(mutated))

    def test_low_risk_hide_is_narrow_and_other_d1_stays_fresh(self):
        combined = "\n".join((self.agents, self.risk, self.a90_attended))
        self.assertIn("UI-only native-init `hide`", combined)
        self.assertIn(
            "Require one fresh explicit operator approval for every other",
            self.risk,
        )
        self.assertIn("service start or stop", self.a90_attended)

    def test_frontier_records_terminal_e2_without_live_authority(self):
        normalized_goal = " ".join(self.goal.split())
        normalized_agents = " ".join(self.agents.split())
        normalized_p280_audit = " ".join(
            self.p280_resume_femto_audit.split()
        )
        self.assertIn("direct PID1", normalized_goal)
        self.assertIn("P2.58A passed terminal stage", normalized_goal)
        self.assertIn(
            "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK", self.goal
        )
        self.assertIn("P2.58A complete/closed, F1", self.goal)
        self.assertIn("E3-E4 next", self.goal)
        self.assertIn("P2.82 consumed one exact approval", normalized_agents)
        self.assertIn("terminal failure `0x8e/detail=0xc10`", normalized_agents)
        self.assertIn("No accepted ACM endpoint appeared", normalized_agents)
        self.assertIn("Child suspend", normalized_agents)
        self.assertIn("were not reached", normalized_agents)
        self.assertIn("swallowed clock errors", self.goal)
        self.assertIn(
            "PASS_P280_RESUME_FEMTO_EUD_INSTRUMENTATION_AUDIT_HOST_ONLY",
            self.p280_resume_femto_audit,
        )
        self.assertIn(
            "does not prove that `dwc3_msm_runtime_resume()`",
            normalized_p280_audit,
        )
        self.assertIn(
            "It does not update `usb_phy.flags`",
            normalized_p280_audit,
        )
        self.assertIn(
            "P2.80 itself is closed and immutable",
            normalized_p280_audit,
        )
        self.assertIn("Typed Retained Evidence", self.process)
        self.assertIn("NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK", self.process)
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
            "No S22+ F1 live run is currently authorized", normalized_goal
        )

    def test_archived_policy_is_not_runtime_dependency(self):
        self.assertIn(
            "Unreachable retired helpers and historical reports are not",
            self.process,
        )
        self.assertIn("Archived text is evidence only", self.goal)


if __name__ == "__main__":
    unittest.main()
