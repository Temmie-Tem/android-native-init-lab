import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS_REVIEW_THRESHOLD_LINES = 220
AGENTS_HARD_MAX_LINES = 260
GOAL_REVIEW_THRESHOLD_LINES = 800
GOAL_HARD_MAX_LINES = 900
ATTENDED_REQUIRED_CLAUSES = (
    "Status: `H0_IMPLEMENTED_STATIC_GO_NO_LIVE_MANIFEST`",
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
A90_TARGET_REQUIRED_CLAUSES = (
    "This policy refactor is H0 only; no A90 D0, D1, F1, approval, or standing attended session is active merely because this file exists.",
    "Their stricter v1 state machines remain binding on the existing v1 runners until a replacement runner is implemented, tested, and independently reviewed against this contract.",
    "the exact A90 target/profile and current resident boot identity;",
    "the exact ready rollback identity and recovery path;",
    "an exact command/action allowlist;",
    "an explicit expiry no later than eight hours after opening;",
    "an explicit positive action budget no greater than 32;",
    "the return-health predicate and device-effect runner closure.",
    "Announce each action, send it once to the exact A90, append one compact action result, and decrement the action budget. No blind automatic loop is permitted.",
    "Forbid partition payloads, arbitrary shell expansion, persistent settings, credential changes, security-state changes, package installation, rootfs replacement, and recovery-path mutation.",
    "End the session on expiry, budget exhaustion, operator absence, target or resident identity change, lost rollback/recovery, an unallowlisted effect, explicit operator stop, or a device-safety failure.",
    "Do not resend the uncertain device action.",
    "continue within the same session only if target, resident, rollback, allowlist, device-effect runner, expiry, and remaining budget are unchanged.",
    "If observer failure cannot be distinguished from target ambiguity, control loss, or resident-health failure, end the session and select the predeclared recovery path.",
    "The same confirmed device-effect failure twice stops live A90 experimentation; the same host parser defect twice stops only that parser implementation.",
    "Candidate replay is forbidden: the runner must never retry the candidate.",
    "once `RESIDENT_HEALTHY` is durably recorded, a later Debian experiment refutation or observer-only no-proof does not retroactively fail installation and does not require rollback.",
    "The first live use of this new terminal requires a runner/schema update, focused tests, independent safety review, connected preflight, and a fresh exact approval; this document alone is not executable authority.",
)


def normalized(text):
    return " ".join(text.split())


def attended_contract_issues(text):
    value = normalized(text)
    return tuple(
        clause for clause in ATTENDED_REQUIRED_CLAUSES if clause not in value
    )


def a90_target_contract_issues(text):
    value = normalized(text)
    return tuple(
        clause for clause in A90_TARGET_REQUIRED_CLAUSES if clause not in value
    )


class DeviceActionProcessV2DocsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        cls.goal = (ROOT / "GOAL.md").read_text(encoding="utf-8")
        cls.goal_a90 = (ROOT / "GOAL_A90.md").read_text(encoding="utf-8")
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
        cls.a90_target = (
            ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        cls.s22_target = (
            ROOT
            / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
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
        self.assertLessEqual(len(self.a90_target.splitlines()), 260)
        self.assertLessEqual(len(self.s22_target.splitlines()), 260)
        self.assertLessEqual(len(self.claude.splitlines()), 40)

    def test_no_candidate_policy_is_active(self):
        active_text = "\n".join((self.agents, self.goal, self.claude))
        self.assertNotIn("POLICY_STATE=ACTIVE", active_text)
        self.assertNotIn("BEGIN_S22PLUS", active_text)
        self.assertIn("Policy edits are H0 and grant no D0, D1, or F1", self.agents)
        self.assertIn(
            "No S22+ F1 live run is currently authorized",
            " ".join(self.goal.split()),
        )
        self.assertIn(
            "No A90 F1, D1, attended continuation",
            " ".join(self.goal_a90.split()),
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
        self.assertIn("must never retry the candidate", normalized(self.agents))
        self.assertIn("Only a separately invoked `recover` action", self.process)
        self.assertIn("does not retransmit automatically", self.process)

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
            (
                self.agents,
                self.process,
                self.risk,
                self.a90_attended,
                self.a90_target,
            )
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

    def test_generic_d1_stays_fresh_and_a90_session_is_bounded(self):
        combined = "\n".join(
            (self.agents, self.risk, self.a90_attended, self.a90_target)
        )
        self.assertIn("UI-only native-init `hide`", combined)
        self.assertIn(
            "Require one fresh explicit operator approval for every other",
            self.risk,
        )
        self.assertIn("service start or stop", self.a90_attended)
        self.assertIn("A90_D1_ATTENDED_SESSION_V1", self.a90_target)
        self.assertIn("no later than eight hours", self.a90_target)
        self.assertIn("no greater than 32", self.a90_target)

    def test_target_registry_and_a90_read_order_are_binding(self):
        self.assertIn(
            "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md",
            self.agents,
        )
        self.assertIn(
            "docs/operations/targets/A90_TARGET_CONTRACT.md",
            self.agents,
        )
        self.assertIn(
            "`AGENTS.md -> A90_TARGET_CONTRACT.md -> GOAL_A90.md`",
            self.a90_target,
        )
        self.assertIn("cannot grant device authority", self.a90_target)

    def test_a90_separates_device_safety_from_experiment_proof(self):
        for token in (
            "BASELINE_HEALTHY",
            "RESIDENT_HEALTHY",
            "RECOVERY_REQUIRED",
            "PROVED",
            "REFUTED",
            "NO_PROOF_OBSERVER",
            "PASS_A90_RESIDENT_INSTALLED",
        ):
            self.assertIn(token, self.a90_target)
        compact = normalized(self.a90_target)
        self.assertIn(
            "do not by themselves make a previously verified resident boot unsafe",
            compact,
        )
        self.assertIn("must never retry the candidate", compact)

    def test_a90_cannot_relax_common_permanent_boundaries(self):
        compact = normalized(self.a90_target)
        for clause in (
            "cannot relax boot-only payload scope",
            "forbidden raw-action list",
            "exact target isolation",
            "rollback availability",
            "candidate no-replay",
            "private evidence handling",
            "demonstrated physical recovery",
        ):
            self.assertIn(clause, compact)
        self.assertIn("any non-boot partition", compact)
        self.assertIn("S22+ received no command", self.a90_target)

    def test_a90_fast_path_rejects_each_load_bearing_mutation(self):
        source = normalized(self.a90_target)
        self.assertEqual(a90_target_contract_issues(source), ())
        for index, clause in enumerate(A90_TARGET_REQUIRED_CLAUSES):
            with self.subTest(clause=clause):
                mutated = source.replace(clause, f"removed-a90-clause-{index}", 1)
                self.assertIn(clause, a90_target_contract_issues(mutated))

    def test_frontier_records_terminal_e2_without_live_authority(self):
        normalized_goal = " ".join(self.goal.split())
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
        self.assertIn("P2.84-through-P2.90", normalized_goal)
        self.assertIn("P2.82", normalized_goal)
        self.assertIn("docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md", self.agents)
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
