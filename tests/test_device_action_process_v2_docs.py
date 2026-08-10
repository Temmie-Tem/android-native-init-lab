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
    "This file alone neither arms A90 nor opens a D1/F1 campaign.",
    "their stricter v1 state machines are implementation compatibility constraints on existing runners until changed and tested; they do not narrow trial policy or require a campaign-level planner.",
    "Under the active trial, the agent selects and iterates exact allowlisted D1 effects while the exact resident is `HEALTHY` and one presence mode below holds.",
    "Policy imposes no per-action approval or action/time budget.",
    "The permanent A90 exception survives retirement but grants no authority by itself.",
    "Qualified unattended mode (`A90_UNATTENDED_RESIDENT_D1_V1`).",
    "reconfirmed by fresh bounded D0 before every ordinal.",
    "`SWITCHROOT_EXPERIMENT` is the currently qualified action.",
    "that lane is policy-ready but not executable. Never assert `--operator-attended` while the operator is absent or asleep.",
    "the exact A90 target/profile and current resident boot identity;",
    "the exact ready rollback identity and recovery path;",
    "an exact command/action allowlist;",
    "an explicit positive duration no greater than eight hours;",
    "an explicit positive action budget no greater than 32;",
    "the return-health predicate and device-effect runner closure.",
    "Announce each action, send it once, append one compact result, and decrement the budget. No blind automatic loop is permitted.",
    "Forbid partition payloads, arbitrary shell expansion, persistent settings, credential/security changes, package/rootfs changes, and recovery mutation.",
    "End this attended compatibility session on expiry/budget exhaustion, operator absence, identity change, lost rollback/recovery, an unallowlisted effect, operator stop, or device-safety failure.",
    "Never automatically resend the uncertain device action.",
    "Continue only while target, resident, rollback, allowlist, effect runner, expiry, and budget are unchanged.",
    "If observer failure cannot be distinguished from target ambiguity, control loss, or resident-health failure, end the session and select the predeclared recovery path.",
    "The same confirmed device-effect failure twice stops live A90 experimentation; the same host parser defect twice stops only that parser implementation.",
    "Candidate replay is forbidden: the runner must never retry the candidate.",
    "once `RESIDENT_HEALTHY` is durably recorded, a later Debian experiment refutation or observer-only no-proof does not retroactively fail installation and does not require rollback.",
    "The existing v1 runner's first use of this terminal requires its schema update, focused tests, review, connected preflight, and compatibility binding; this document alone creates no active campaign.",
)
A90_UNATTENDED_D1_REQUIRED_CLAUSES = (
    "Automatic native return must remain proved; physical recovery remains demonstrated and available when the operator returns.",
    "S22+ never inherits this exception.",
    "Its expected terminal is automatic native return.",
    "F1, payload/partition writes, persistent settings, credentials, security state, package/rootfs/recovery mutation, and actions expected to need physical entry are ineligible.",
    "Each ordinal has one durable intent, one dispatch, and no automatic replay.",
    "No next ordinal starts until exact `RESIDENT_HEALTHY` is durable.",
    "An absent or late ACM/NCM endpoint after an announced transition enters common `HEALTH_PENDING`; it is not by itself target ambiguity or resident-health failure.",
    "control loss or `RECOVERY_REQUIRED` parks with no new effect",
    "operator return and predeclared recovery are then required.",
    "Target ambiguity, resident mismatch, or lost physical recovery stops the lane under the permanent boundaries.",
    "The agent may repair an H0 observer and start a new ordinal without acknowledgement only after independently re-establishing exact health",
    "the same unresolved observer defect must not become a blind loop.",
    "A90 F1 is always attended",
)

FAST_LOOP_HEALTH_REQUIRED_CLAUSES = (
    "A missing, late, timed-out, or malformed observation is not by itself a device-health or recovery failure.",
    "Endpoint absence is not target ambiguity; ambiguity requires multiple plausible targets or conflicting bound identity.",
    "`HEALTH_PENDING`",
    "`HOST_OBSERVER_FAILURE`",
    "`RECOVERY_PENDING_PARKED`",
    "Until exact health and recovery establish `HEALTHY`, permit only passive bounded observation",
    "Never replay the uncertain action.",
    "A timeout parks rather than closes;",
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
        clause
        for clause in A90_TARGET_REQUIRED_CLAUSES
        + A90_UNATTENDED_D1_REQUIRED_CLAUSES
        if clause not in value
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
        cls.a90_d1_runner = (
            ROOT
            / "workspace/public/src/scripts/server-distro/"
            "a90_transition_d1_session_v1.py"
        ).read_text(encoding="utf-8")
        cls.a90_unattended_runner = (
            ROOT
            / "workspace/public/src/scripts/server-distro/"
            "a90_unattended_resident_d1_v1.py"
        ).read_text(encoding="utf-8")
        cls.a90_unattended_policy_report = (
            ROOT
            / "docs/reports/"
            "A90_UNATTENDED_RESIDENT_D1_POLICY_H0_2026-08-03.md"
        ).read_text(encoding="utf-8")
        cls.a90_unattended_runner_report = (
            ROOT
            / "docs/reports/"
            "A90_UNATTENDED_RESIDENT_D1_RUNNER_H0_2026-08-03.md"
        ).read_text(encoding="utf-8")
        cls.s22_target = (
            ROOT
            / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
        ).read_text(encoding="utf-8")
        cls.a90_ledger = (
            ROOT / "docs/operations/CAMPAIGN_LEDGER_A90.md"
        ).read_text(encoding="utf-8")
        cls.s22_ledger = (
            ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
        ).read_text(encoding="utf-8")
        cls.p280_resume_femto_audit = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P280_RESUME_FEMTO_EUD_"
            "INSTRUMENTATION_AUDIT_H0_2026-07-28.md"
        ).read_text(encoding="utf-8")
        cls.post_p296_attribution = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_POST_P296_GADGET_START_RETURN_"
            "ATTRIBUTION_H0_2026-08-03.md"
        ).read_text(encoding="utf-8")
        cls.archived_agents = (
            ROOT / "docs/archive/policy/AGENTS_PRE_PROCESS_V2_2026-07-21.md"
        ).read_text(encoding="utf-8")
        cls.archived_goal = (
            ROOT / "docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md"
        ).read_text(encoding="utf-8")
        cls.archived_goal_through_p313 = (
            ROOT
            / "docs/archive/roadmaps/"
            "GOAL_THROUGH_P312_AND_P313_DESIGN_2026-08-10.md"
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
        self.assertLessEqual(len(self.s22_target.splitlines()), 260)
        self.assertLessEqual(len(self.claude.splitlines()), 40)

    def test_trial_does_not_reactivate_consumed_runs(self):
        active_text = "\n".join((self.agents, self.goal, self.claude))
        self.assertNotIn("POLICY_STATE=ACTIVE", active_text)
        self.assertNotIn("BEGIN_S22PLUS", active_text)
        self.assertIn("Status: **RETIRED**", self.agents)
        self.assertIn(
            "no longer grant standing D0, procedural autonomy, or an override",
            normalized(self.agents),
        )
        self.assertIn(
            "It grants no standing D0, autonomy, or per-candidate approval waiver.",
            normalized(self.goal),
        )
        self.assertIn("grants no device authority", normalized(self.goal_a90))
        self.assertIn(
            "Target identities, artifacts, transports, evidence, recovery, and commands never cross between the two goals.",
            normalized(self.goal_a90),
        )

    def test_retired_trial_is_historical_and_ordinary_authority_controls(self):
        compact = normalized(self.agents)
        for clause in (
            "For a new device effect that already satisfies every permanent boundary",
            "exact target identity matches its bound profile (D0/D1/F1);",
            "the target-contract presence predicate is true (D1/F1; unattended only where both contracts expressly allow it).",
            "These are not the exhaustive safety checks.",
            "The agent owns goal selection, experiment design, and iteration.",
            "Do not require a campaign-level planner or runner.",
            "Legacy v1 approval/time/action limits remain implementation constraints",
            "Attendance loss stops F1 and all D1 except the qualified A90 lane.",
            "Only its qualified A90 resident D1 lane may be unattended; every F1 and all other D1 stay attended.",
            "Contract Revision 2 and permanent boundaries remain; adopt this autonomy or lapse only it.",
            "F1 exclusivity belongs to target-identity gate 1, not a fifth gate.",
            "A target becomes F1-armed when its journal durably records candidate intent",
            "Disarm only after exact `HEALTHY` is durable;",
            "An independent `PASS_GO` qualifies a capability, not a run.",
            "Reuse it across candidates, campaigns, manifests, qualifications, and ordinals while its named execution-critical hashes are unchanged and no new hazard or incident occurs.",
            "Fresh qualification and any runner binding still apply.",
        ):
            self.assertIn(clause, compact)
        self.assertNotIn("attendance predicate true (F1 only)", compact)
        self.assertNotIn("Every other validator", self.agents)
        self.assertNotIn("Only these four may refuse execution", self.agents)
        self.assertIn(
            "The retained trial text is historical and grants no current standing D0, procedural autonomy, or override.",
            normalized(self.claude),
        )
        self.assertIn(
            "No retired trial clause waives per-candidate approval.",
            normalized(self.s22_target),
        )
        self.assertIn("grants no device authority", normalized(self.goal_a90))
        self.assertIn(
            "first `CAMPAIGN_CLOSED` action row for each distinct campaign ID",
            normalized(self.a90_ledger),
        )
        self.assertIn("Duplicate close", self.a90_ledger)
        self.assertIn(
            "The trial retirement calculation is closed",
            self.s22_ledger,
        )
        self.assertIn("Duplicate close", self.s22_ledger)

    def test_a90_unattended_lane_is_policy_ready_but_not_falsely_executable(self):
        compact = normalized(self.a90_target)
        for clause in (
            "Qualified unattended mode (`A90_UNATTENDED_RESIDENT_D1_V1`).",
            "reconfirmed by fresh bounded D0 before every ordinal.",
            "`SWITCHROOT_EXPERIMENT` is the currently qualified action.",
            "No next ordinal starts until exact `RESIDENT_HEALTHY` is durable.",
            "that lane is policy-ready but not executable.",
            "Never assert `--operator-attended` while the operator is absent or asleep.",
        ):
            self.assertIn(clause, compact)
        self.assertEqual(a90_target_contract_issues(self.a90_target), ())
        self.assertIn(
            "Device effects require attendance except the exact A90 resident D1 lane delegated below; F1 is never unattended",
            normalized(self.agents),
        )
        self.assertIn(
            'parser.add_argument("--operator-attended", action="store_true")',
            self.a90_d1_runner,
        )
        self.assertIn(
            "H0_PASS_GO_POLICY_CLARIFIED_NO_LIVE_AUTHORITY",
            self.a90_unattended_policy_report,
        )
        self.assertIn(
            "capability qualification, not a per-run approval",
            normalized(self.a90_unattended_policy_report),
        )
        self.assertIn(
            'WORKFLOW = "A90_UNATTENDED_RESIDENT_D1_V1"',
            self.a90_unattended_runner,
        )
        self.assertNotIn(
            'parser.add_argument("--operator-attended"',
            self.a90_unattended_runner,
        )
        self.assertIn(
            "H0_IMPLEMENTED_STATIC_PASS_CAPABILITY_REVIEW_PASS_GO",
            self.a90_unattended_runner_report,
        )

    def test_s22_retired_trial_and_live_attendance_are_explicit(self):
        compact = normalized(self.s22_target)
        for clause in (
            "This file alone neither arms the target nor opens a D0/D1/F1 action.",
            "The common Fast-Loop trial is retired; it grants no standing D0, attended autonomy, or per-candidate approval waiver.",
            "The operator must remain present and able to perform the action's predeclared return or recovery step.",
            "the operator must be able to perform that physical step within its bound.",
            "Attendance loss freezes new effects; it never authorizes replay of the uncertain action.",
            "D1 requires the fresh exact authority specified by the live common and target rules.",
            "Process-v2 requires a new immutable manifest, exact D0, one fresh candidate/rollback binding, and the fresh exact approval required after Fast-Loop retirement.",
            "A90 approvals, health evidence, transports, artifacts, and resident-promotion rules never apply to S22+.",
        ):
            self.assertIn(clause, compact)

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
        self.assertIn("candidate replay is forbidden", normalized(self.agents))
        self.assertIn("Only a separately invoked `recover` action", self.process)
        self.assertIn("does not retransmit automatically", self.process)

    def test_fast_loop_separates_observation_delay_from_device_failure(self):
        compact = normalized(self.agents)
        for clause in FAST_LOOP_HEALTH_REQUIRED_CLAUSES:
            self.assertIn(clause, compact)
        self.assertIn("HEALTH_PENDING", self.a90_target)
        self.assertIn("never resend the uncertain action", normalized(self.a90_target))
        self.assertIn("HEALTH_PENDING", self.s22_target)
        self.assertIn("uncertain candidate is never replayed", normalized(self.s22_target))
        for ledger in (self.a90_ledger, self.s22_ledger):
            self.assertIn("Device safety is recorded independently", ledger)
            self.assertIn("information yield", ledger)
            self.assertIn("NO_PROOF_OBSERVER", ledger)
            self.assertIn("structured result", ledger)

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
        combined = normalized("\n".join(
            (
                self.agents,
                self.process,
                self.risk,
                self.a90_attended,
                self.a90_target,
            )
        ))
        for token in (
            "operator-attended-v1",
            "attended_window_sec",
            "pre_handoff_attempt_limit",
            "handoff_attempt_limit",
            "attended-window-open",
            "attended-handoff-started",
            "cannot be applied to a candidate after candidate intent",
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

    def test_legacy_d1_runner_stays_bounded_until_aligned(self):
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
        self.assertIn("existing v1 runner", self.a90_target)
        self.assertIn("positive duration no greater than eight hours", self.a90_target)
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
        self.assertIn("neither arms A90 nor opens a D1/F1 campaign", self.a90_target)

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
        required = A90_TARGET_REQUIRED_CLAUSES + A90_UNATTENDED_D1_REQUIRED_CLAUSES
        for index, clause in enumerate(required):
            with self.subTest(clause=clause):
                mutated = source.replace(clause, f"removed-a90-clause-{index}", 1)
                self.assertIn(clause, a90_target_contract_issues(mutated))

    def test_frontier_records_closed_p314_and_h0_qualified_p315(self):
        normalized_goal = " ".join(self.goal.split())
        self.assertIn("P3.14 is the latest closed live unit", normalized_goal)
        self.assertIn("terminal `0x6705`", normalized_goal)
        self.assertIn("`profile-record-deficit`", normalized_goal)
        self.assertIn("did not construct or execute the restart helper", normalized_goal)
        self.assertIn("deterministic observer self-failure", normalized_goal)
        self.assertIn("`p282_trace_read_snapshot(..., 0)`", normalized_goal)
        self.assertIn("`profile_hits[]` untouched", normalized_goal)
        self.assertIn("`rc=0x6705 records=14 profile0=0 record0=1`", normalized_goal)
        self.assertIn("P3.14 is now consumed and closed", normalized_goal)
        self.assertIn(
            "P3.15 closes the H0 live-profile snapshot ordering repair",
            normalized_goal,
        )
        self.assertIn(
            "first freshly authorized connected D0 selected the exact S22+",
            normalized_goal,
        )
        self.assertIn(
            "No prepared live binding or transaction exists", normalized_goal
        )
        self.assertIn("generation 96, stage `0x90`, item 3", normalized_goal)
        self.assertIn("generation 97, stage `0x90`, item 4", normalized_goal)
        self.assertIn("terminal failure `0x6712`", normalized_goal)
        self.assertIn("`cycle-event-multiplicity`", normalized_goal)
        self.assertIn("runtime terminated before the restart helper", normalized_goal)
        self.assertIn("source-forced sufficient trigger", normalized_goal)
        self.assertIn("not proof that no other pair multiplied", normalized_goal)
        self.assertIn("inherited P3.12 Carrier semantics", normalized_goal)
        self.assertIn("reported only `E2_PROGRESS_OBSERVED`", normalized_goal)
        self.assertIn("This is an observer-decoder incident", normalized_goal)
        self.assertIn("P3.13 is now consumed and closed", normalized_goal)
        self.assertIn("No live authority remains", normalized_goal)
        self.assertIn("role: strict five events, `5/64`", normalized_goal)
        self.assertIn("cycle: a dedicated 25-event set, 37 records clean", normalized_goal)
        self.assertIn("41 clean records and 49 for one bounded drift", normalized_goal)
        self.assertIn("count-model correction does not relax fail-closed", normalized_goal)
        self.assertIn("exactly one diagnostic restorative restart", normalized_goal)
        self.assertIn("revokes every cycle-causal claim", normalized_goal)
        self.assertIn("`0x6c01..0x6fff`", normalized_goal)
        self.assertIn("P3.11's historical `0x6801..0x680c`", normalized_goal)
        self.assertIn("1,023 nonzero masks", normalized_goal)
        self.assertIn("zero new trace records", normalized_goal)
        self.assertIn("109,461 mask-by-position failure cells", normalized_goal)
        self.assertIn("6,741 failure round trips pass", normalized_goal)
        self.assertIn("inherited 1,200 B outputs", normalized_goal)
        self.assertIn("at least 251,450 cells", normalized_goal)
        self.assertIn("real Process-v2 evidence adapter", normalized_goal)
        self.assertIn("registered-not-satisfied", normalized_goal)
        self.assertIn("missing or failed closure blocks the package", normalized_goal)
        self.assertIn("P3.14 is the selected minimal successor", normalized_goal)
        self.assertIn("P3.14 does not activate the optional diagnostic-only continuation", normalized_goal)
        self.assertIn("clean stop is 14 records", normalized_goal)
        self.assertIn("host-qualified-independent-review-pending", normalized_goal)
        self.assertIn("validator precedes the parent packager", normalized_goal)
        self.assertIn("Configured host waits total 880 seconds", normalized_goal)
        self.assertIn("default guard is only 360 seconds", normalized_goal)
        self.assertIn("exact live `approval_binding_sha256`", normalized_goal)
        self.assertIn("Existing v2 evidence remains readable under its original meaning", normalized_goal)
        self.assertIn("Unknown or mixed versions fail closed", normalized_goal)
        self.assertIn("68 frozen `SOURCE_KEYS`", normalized_goal)
        self.assertIn("no kernel rebuild or Full-LTO was performed", normalized_goal)
        self.assertIn("The consumed candidate is never replayable", normalized_goal)
        self.assertIn("Archived Goal: S22+ Through P3.12 and P3.13 Design", self.archived_goal_through_p313)
        self.assertIn("P3.12 is the latest closed live unit", self.archived_goal_through_p313)
        self.assertIn("docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md", self.agents)
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

    def test_archived_policy_is_not_runtime_dependency(self):
        self.assertIn(
            "Unreachable retired helpers and historical reports are not",
            self.process,
        )
        self.assertIn("Archived text is evidence only", self.goal)
        self.assertIn(
            "Archived text is evidence only",
            self.archived_goal_through_p313,
        )


if __name__ == "__main__":
    unittest.main()
