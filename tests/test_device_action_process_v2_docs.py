import hashlib
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


RESULT_CONTRACT_ARMING_REQUIRED_CLAUSES = (
    "every terminal state of the result contract, including each failure bucket,"
    " decodes to its intended classification from a synthesized retained"
    " representation",
    "must exercise the real encoder, the real carrier representation, and the"
    " real host decoder rather than a stand-in for any of them",
    "The gate binds the encode and decode path, not the device condition behind"
    " it.",
    "reproducing the physical condition that would emit it is neither required"
    " nor sufficient",
    "A capability proof does not satisfy this precondition.",
    "this gate binds the observer",
    "`NO_PROOF_OBSERVER`",
)

EXPERIMENT_EXECUTABILITY_REQUIRED_CLAUSES = (
    "`NO_PROOF_EXPERIMENT_PRECONDITION`",
    "`EXPERIMENT_EXECUTABILITY_CLOSURE`",
    "explicitly permanent common qualification boundary",
    "`UNMODELED_EXPERIMENT_DEPENDENCY_PRECONDITION`",
    "It has no expiry.",
    "Every new relation family requires proportional independent review before use.",
    "must-bind consumer set",
    "The first registered family is `FW_DEVLINK_DT_SUPPLIER_CLOSURE`.",
    "The second registered family is `DEVICE_INSTANTIATION_CLOSURE`.",
    "The third registered family is `DRIVER_CONSUMED_DT_REFERENCE_CLOSURE`.",
    "default OF platform population, SPMI controller child enumeration, parent-driver OF child population, and OF I2C-child creation",
    "Every node emitted by any family re-enters **all** registered families on the next iteration.",
    "Root-only or single-family analysis is forbidden.",
    "`qcom,wrapper-core` reference",
    "A direct driver-consumed reference is neither a fw_devlink supplier edge nor proof that the referenced driver instantiated the consumer.",
    "each fixed-point iteration's input frontier",
    "Each causal claim must also name its **evaluability preconditions**",
    "Qualification mechanically enforces presence and coverage of those declarations; it does not certify their causal truth merely because text exists.",
    "A raw scan of every phandle is not equivalent to the kernel parser and is forbidden as closure evidence.",
    "the complete parser-table rows, count, order, source identity, and each row's `optional` bit;",
    "Whether an optional row is parsed depends on the exact `fw_devlink` mode and `fw_devlink.strict`;",
    "Changing the global kernel policy to `fw_devlink=off`, `fw_devlink=permissive`, or a non-strict equivalent is not an admissible remedy",
    "attribute absent, attribute present with `0`, and attribute present with `1`",
    "Absence means unavailable authority, not false; the value is a boolean and never names the unresolved supplier.",
)

RETIRED_FAST_LOOP_OPERATIONAL_CLAUSES = (
    "only these procedural authority gates may refuse it",
    "Other host-only schema, shape, and evidence failures are H0 bugs to fix and rerun, not new device-authority gates.",
    "H0 | Unlimited. Rule 7 suspended. Fix and continue.",
    "D0 | Autonomous for a resolved exact target. No approval.",
    "D1 | Autonomous under the target presence mode.",
    "F1 | Autonomous while attended. No per-candidate approval.",
    "The agent owns goal selection, experiment design, and iteration. Do not require a campaign-level planner or runner.",
    "Legacy v1 approval/time/action limits remain implementation constraints until their runners change; they do not define the trial policy.",
    "An F1 run parked while awaiting a required physical operator step remains F1-armed.",
    "Host-only work continues during a park; no second candidate may be armed, and a park is not an abort.",
    "F1 exclusivity belongs to target-identity gate 1, not a fifth gate.",
    "Each target contract defines its presence predicate.",
    "A missing, late, timed-out, or malformed observation is not by itself a device-health or recovery failure.",
    "Endpoint absence is not target ambiguity; ambiguity requires multiple plausible targets or conflicting bound identity.",
    "Unresolved observation freezes new effects as `HEALTH_PENDING`, `HOST_OBSERVER_FAILURE`, or `RECOVERY_PENDING_PARKED`.",
    "Until exact health and recovery establish `HEALTHY`, permit only passive bounded observation, re-enumeration stabilization, H0 observer repair/replay, and exact recovery.",
    "A timeout parks rather than closes; confirmed negative health enters recovery.",
    "Attendance loss stops F1 and all D1 except the qualified A90 lane.",
    "Routine narrative evidence is the commit body: attempt, result including no-proof, judgment, work, and a `Validation:` line.",
    "Append the structured row to the per-target campaign ledger: `docs/operations/CAMPAIGN_LEDGER_S22PLUS.md` or `docs/operations/CAMPAIGN_LEDGER_A90.md`.",
    "Write a separate report only for a new capability, a new hazard class, an incident, or a genuinely ambiguous device-safety result.",
    "No per-run prose, no review ladder, and no per-candidate policy document.",
    "A superseded report moves to `docs/archive/reports/`; location is the authority signal.",
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


def retired_fast_loop_authority_issues(text):
    value = normalized(text)
    return tuple(
        clause for clause in RETIRED_FAST_LOOP_OPERATIONAL_CLAUSES
        if clause in value
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
        retired_fast_loop_path = (
            ROOT
            / "docs/archive/policy/"
            "AGENTS_INTERIM_FAST_LOOP_RETIRED_2026-08-03.md"
        )
        cls.retired_fast_loop_bytes = retired_fast_loop_path.read_bytes()
        cls.retired_fast_loop = cls.retired_fast_loop_bytes.decode("utf-8")
        cls.archive_index = (
            ROOT / "docs/archive/README.md"
        ).read_text(encoding="utf-8")
        cls.archived_goal = (
            ROOT / "docs/archive/roadmaps/GOAL_PRE_PROCESS_V2_2026-07-21.md"
        ).read_text(encoding="utf-8")
        cls.archived_goal_through_p313 = (
            ROOT
            / "docs/archive/roadmaps/"
            "GOAL_THROUGH_P312_AND_P313_DESIGN_2026-08-10.md"
        ).read_text(encoding="utf-8")
        cls.p313_design = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P313_POST_BIND_RESUME_CYCLE_DESIGN_H0_2026-08-10.md"
        ).read_text(encoding="utf-8")
        cls.p313_gap = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P313_STOP_MULTIPLICITY_AND_CONTINUATION_GAP_H0_2026-08-10.md"
        ).read_text(encoding="utf-8")
        cls.p313_decoder_incident = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P313_INTERMEDIATE_CONTRADICTION_DECODER_INCIDENT_2026-08-10.md"
        ).read_text(encoding="utf-8")
        cls.p314_design = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P314_SOURCE_NORMALIZED_CYCLE_SUCCESSOR_DESIGN_H0_2026-08-10.md"
        ).read_text(encoding="utf-8")
        cls.p314_incident = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P314_LIVE_PROFILE_SNAPSHOT_INCIDENT_2026-08-10.md"
        ).read_text(encoding="utf-8")
        cls.p316_incident = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P316_MAX77705_SYNC_PROBE_"
            "CONTRADICTION_INCIDENT_2026-08-12.md"
        ).read_text(encoding="utf-8")
        cls.p317_design = (
            ROOT
            / "docs/reports/"
            "S22PLUS_FYG8_P317_EXPERIMENT_EXECUTABILITY_"
            "CLOSURE_DESIGN_H0_2026-08-12.md"
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
        self.assertNotIn("Status: **RETIRED**", self.agents)
        self.assertIn("Status: **RETIRED**", self.retired_fast_loop)
        self.assertIn(
            "no longer grant standing D0, procedural autonomy, or an override",
            normalized(self.retired_fast_loop),
        )
        self.assertIn(
            "historical evidence only and grants no current authority",
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
        historical = normalized(self.retired_fast_loop)
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
        ):
            self.assertIn(clause, historical)
        for clause in (
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
        self.assertEqual(len(self.retired_fast_loop.splitlines()), 82)
        self.assertEqual(len(self.retired_fast_loop_bytes), 4898)
        self.assertEqual(
            hashlib.sha256(self.retired_fast_loop_bytes).hexdigest(),
            "e270865908821ff1221665a83a22707ae0dcde140e18e5ba600b82423c34dbc7",
        )
        self.assertIn(
            "It is inert historical evidence and grants no current authority.",
            self.archive_index,
        )
        self.assertIn(
            "AGENTS_INTERIM_FAST_LOOP_RETIRED_2026-08-03.md",
            self.agents,
        )

    def test_archiving_keeps_retired_authority_out_of_live_contract(self):
        active = normalized(self.agents)
        archived = normalized(self.retired_fast_loop)
        self.assertNotIn("## Interim Fast-Loop Rules", self.agents)
        for clause in (
            "The retired Interim Fast-Loop trial contract is preserved byte-for-byte at `docs/archive/policy/AGENTS_INTERIM_FAST_LOOP_RETIRED_2026-08-03.md`; it is historical evidence only and grants no current authority.",
            "This file contains the repository-wide invariants and the binding target registry.",
            "Select exactly one target contract before target-specific work.",
            "Historical or draft policies under `docs/archive/` or elsewhere are evidence only, even if their text says `ACTIVE`.",
            "`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`",
            "Do not add a device step when host-only work can answer the question.",
        ):
            self.assertIn(clause, active)
        for clause in RETIRED_FAST_LOOP_OPERATIONAL_CLAUSES:
            self.assertIn(clause, archived)
        self.assertEqual(retired_fast_loop_authority_issues(self.agents), ())

    def test_retired_fast_loop_authority_reinsertion_is_rejected(self):
        for clause in RETIRED_FAST_LOOP_OPERATIONAL_CLAUSES:
            with self.subTest(clause=clause):
                self.assertEqual(
                    retired_fast_loop_authority_issues(
                        f"{self.agents}\n{clause}\n"
                    ),
                    (clause,),
                )

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
        compact = normalized(self.retired_fast_loop)
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

    def test_f1_arming_requires_a_reportable_failure_contract(self):
        value = normalized(self.process)
        for clause in RESULT_CONTRACT_ARMING_REQUIRED_CLAUSES:
            self.assertIn(clause, value)

    def test_result_contract_precondition_rejects_each_load_bearing_mutation(self):
        value = normalized(self.process)
        for index, clause in enumerate(RESULT_CONTRACT_ARMING_REQUIRED_CLAUSES):
            mutated = value.replace(clause, "")
            self.assertNotEqual(
                mutated,
                value,
                f"clause {index} is absent from the process contract",
            )
            missing = tuple(
                other
                for other in RESULT_CONTRACT_ARMING_REQUIRED_CLAUSES
                if other not in mutated
            )
            self.assertIn(clause, missing)

    def test_process_v2_requires_experiment_executability_closure(self):
        value = normalized(self.process)
        for clause in EXPERIMENT_EXECUTABILITY_REQUIRED_CLAUSES:
            self.assertIn(clause, value)

    def test_executability_closure_rejects_each_load_bearing_mutation(self):
        source = normalized(self.process)
        for index, clause in enumerate(EXPERIMENT_EXECUTABILITY_REQUIRED_CLAUSES):
            with self.subTest(clause=clause):
                mutated = source.replace(
                    clause, f"removed-exec-clause-{index}", 1
                )
                missing = tuple(
                    other
                    for other in EXPERIMENT_EXECUTABILITY_REQUIRED_CLAUSES
                    if other not in mutated
                )
                self.assertIn(clause, missing)

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

    def test_frontier_records_closed_p315_outer_work_drift(self):
        normalized_goal = " ".join(self.goal.split())
        normalized_p313 = " ".join(
            (
                self.p313_design
                + self.p313_gap
                + self.p313_decoder_incident
            ).split()
        )
        normalized_p314 = " ".join(
            (self.p314_design + self.p314_incident).split()
        )
        self.assertIn("P3.17 is the latest closed live unit", normalized_goal)
        self.assertIn("P3.16 is the preceding closed live unit", normalized_goal)
        self.assertIn("P3.15 is the preceding closed cycle unit", normalized_goal)
        self.assertIn("A=`0x0d3f`", normalized_goal)
        self.assertIn("B=`0x5064`", normalized_goal)
        self.assertIn("path-drift mask `0x04`", normalized_goal)
        self.assertIn("sole `OUTER_WORK` bit", normalized_goal)
        self.assertIn("pullup pairs were zero", normalized_goal)
        self.assertIn("RUN_STOP pairs were two", normalized_goal)
        self.assertIn("gadget-start was one pair", normalized_goal)
        self.assertIn("eight complete `dwc3_otg_sm_work` pairs", normalized_goal)
        self.assertIn("expectation of four", normalized_goal)
        self.assertIn("refutes the clean four-outer-work cycle model", normalized_goal)
        self.assertIn("revokes a cycle-causal claim", normalized_goal)
        self.assertIn("none of this proves whether a USB2 pull-up reached", normalized_goal)
        self.assertIn("`cycle_causal_claim=true`", normalized_goal)
        self.assertIn("P3.14 is now consumed and closed", normalized_goal)
        self.assertIn("P3.15 is also consumed and closed", normalized_goal)
        self.assertIn("historical evidence only and grant no authority", normalized_goal)
        self.assertIn("generation 96, stage `0x90`, item 3", normalized_goal)
        self.assertIn("generation 97, stage `0x90`, item 4", normalized_goal)
        self.assertIn("terminal failure `0x6712`", normalized_goal)
        self.assertIn("inherited P3.12 Carrier semantics", normalized_goal)
        self.assertIn("P3.13 is now consumed and closed", normalized_goal)
        self.assertIn("No live authority remains", normalized_goal)
        self.assertIn("251,450-cell", normalized_goal)
        self.assertIn("real Process-v2 adapter", normalized_goal)
        self.assertIn("validator-before-packager wiring", normalized_goal)
        self.assertIn("without changing the fixed Image or running Full-LTO", normalized_goal)
        self.assertIn("clean 14-record stop snapshot", normalized_goal)
        self.assertIn("neither candidate may be replayed", normalized_goal)
        self.assertIn("`NO_PROOF_EXPERIMENT_PRECONDITION`", normalized_goal)
        self.assertIn(
            "four observer failures, one experiment-precondition failure, and two conclusive `REFUTED` results",
            normalized_goal,
        )
        self.assertIn("`FW_DEVLINK_DT_SUPPLIER_CLOSURE`", normalized_goal)
        self.assertIn("`DEVICE_INSTANTIATION_CLOSURE`", normalized_goal)
        self.assertIn("`DRIVER_CONSUMED_DT_REFERENCE_CLOSURE`", normalized_goal)
        self.assertIn(
            "three roots, three claims, nine claim-to-consumer counterfactuals, and four explicit evaluability preconditions",
            normalized_goal,
        )
        self.assertIn(
            "b9d8b967aed453ab006aa7532592f4fc6413131d775159df4f18daf96ec33334",
            normalized_goal,
        )
        self.assertIn(
            "49859c0957a15ef25cdad98137c5f178eb790f4689ddeb74553971d1a9ce3070",
            normalized_goal,
        )
        self.assertIn(
            "fd27d79883cbdc5e6daab937f0b24ab303fdd8a1c91cf63feb5789975e04c1d3",
            normalized_goal,
        )
        self.assertIn("same 23-node closure after five iterations", normalized_goal)
        self.assertIn("170 raw and 53 deduplicated relations", normalized_goal)
        self.assertIn("effective count from `65 -> 70`", normalized_goal)
        self.assertIn(
            "b4418d8cf0a8aedcb540e53d008720e31202ede823cc6064978463ef3b8d8f9c",
            normalized_goal,
        )
        self.assertIn("generic early loop loads those 69 modules", normalized_goal)
        self.assertIn("`s22plus_max77705_mux_diag.ko`", normalized_goal)
        self.assertIn("dedicated synchronous late `finit_module()`", normalized_goal)
        self.assertIn(
            "two raw property reasons become one deduplicated consumer-to-supplier edge",
            normalized_goal,
        )
        self.assertIn(
            "88b8247e48a1945c8a5f31544336f942c32f9604787e0cd46de0ba5f70f17609",
            normalized_goal,
        )
        for report_name in (
            "S22PLUS_FYG8_P313_POST_BIND_RESUME_CYCLE_DESIGN_H0_2026-08-10.md",
            "S22PLUS_FYG8_P313_STOP_MULTIPLICITY_AND_CONTINUATION_GAP_H0_2026-08-10.md",
            "S22PLUS_FYG8_P314_SOURCE_NORMALIZED_CYCLE_SUCCESSOR_DESIGN_H0_2026-08-10.md",
        ):
            self.assertIn(report_name, normalized_goal)
        self.assertIn("`cycle-event-multiplicity`", normalized_p313)
        self.assertIn("source-forced `phy_suspend_off` multiplicity", normalized_p313)
        self.assertIn("does **not** prove that `phy_suspend_off` was the only multiplied pair", normalized_p313)
        self.assertIn("persisted `E2_PROGRESS_OBSERVED`", normalized_p313)
        self.assertIn("all 126 A outputs and 1,200 B outputs", normalized_p313)
        self.assertIn("exact live `approval_binding_sha256`", normalized_p313)
        self.assertIn("68 frozen `SOURCE_KEYS`", normalized_p313)
        self.assertIn("1,023 nonzero masks", normalized_p313)
        self.assertIn("109,461 combinations", normalized_p313)
        self.assertIn("6,741 accepted combinations", normalized_p313)
        self.assertIn("251,450 cells", normalized_p314)
        self.assertIn("prepackaging validator precedes", normalized_p314)
        self.assertIn("P3.14 is consumed and never replayable", normalized_p314)
        normalized_p316 = normalized(self.p316_incident)
        normalized_p317 = normalized(self.p317_design)
        normalized_ledger = normalized(self.s22_ledger)
        self.assertIn(
            "observer failures 4, experiment-precondition failure 1, and conclusive experiment results 2",
            normalized_p316,
        )
        self.assertIn(
            "original P3.16 `CAMPAIGN_CLOSED` row remains byte-for-byte historical",
            normalized_p316,
        )
        self.assertIn("exactly 28 non-sentinel entries", normalized_p317)
        self.assertIn(
            "raw property edges 2 deduplicated consumer -> supplier edges 1",
            normalized_p317,
        )
        self.assertIn("attribute absent", normalized_p317)
        self.assertIn("present, value `0`", normalized_p317)
        self.assertIn("present, value `1`", normalized_p317)
        self.assertIn("`fw_devlink=off`", normalized_p317)
        self.assertIn("INDEPENDENT REVIEW PASS", normalized_p317)
        self.assertIn(
            "S22PLUS_FYG8_P317_CUSTOM70_PROCESS_V2_OFFLINE_READY_CAPABILITY_V1",
            normalized_p317,
        )
        self.assertIn("independently PASS_GO", normalized_p317)
        self.assertIn("5732cb44797f4a4a", normalized_p317)
        self.assertIn("pass 40/40", normalized_p317)
        self.assertIn(
            "final independent changed-closure review is complete",
            normalized_p317,
        )
        self.assertNotIn(
            "satisfy the required final independent changed-closure review",
            normalized_p317,
        )
        self.assertIn(
            "P316_PROOF_CLASS_CORRECTION_AND_EXPERIMENT_EXECUTABILITY_CLOSURE_DESIGN",
            normalized_ledger,
        )
        self.assertIn(
            "original campaign s22plus-fyg8-p316 ordinal 1",
            normalized_ledger,
        )
        self.assertIn(
            "count its effective class as NO_PROOF_EXPERIMENT_PRECONDITION",
            normalized_ledger,
        )
        self.assertIn(
            "PASS_GO_P317_CUSTOM70_PROCESS_V2_OFFLINE_READY_CAPABILITY_V1",
            normalized_ledger,
        )
        self.assertIn("107 positive retained preimages", normalized_ledger)
        self.assertIn("claim-busy negative invariant", normalized_ledger)
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
