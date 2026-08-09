# AGENTS.md - repository operating contract

Contract-Revision: **2** (supersedes revision 1; 2026-08-03)

## Interim Fast-Loop Rules (operational trial)

Status: **RETIRED**. The trial was activated by operator declaration on 2026-08-03
and retired at 2026-08-03T20:46:02Z, when the first `CAMPAIGN_CLOSED` rows for the two distinct campaign IDs
`s22plus-fyg8-p296` and `s22plus-fyg8-p298` had both been recorded. The terms below are retained as the historical trial contract only.
They no longer grant standing D0, procedural autonomy, or an override of the ordinary target contracts and process documents.
Permanent device, repository, and evidence boundaries remained absolute throughout.

Retirement: end after the first `CAMPAIGN_CLOSED` row for each of two distinct campaign IDs across both ledgers, or on 2026-09-03, whichever comes first.
Duplicate closes and parked campaigns do not count. Contract Revision 2 and permanent boundaries remain; adopt this autonomy or lapse only it. Never extend silently.

The retirement condition above is satisfied. The following trial-only procedural authority, autonomy, health, and evidence terms
are non-operative and remain here only to preserve the contract record for the interval in which the trial was active.

### Procedural authority gates - closed list

For a new device effect that already satisfies every permanent boundary, only
these procedural authority gates may refuse it:

1. exact target identity matches its bound profile (D0/D1/F1);
2. an exact hash-bound rollback is ready when required (D1/F1);
3. the target-contract recovery path is demonstrated and available (D1/F1); and
4. the target-contract presence predicate is true (D1/F1; unattended only where both contracts expressly allow it).

These are not the exhaustive safety checks. Permanent boundaries, artifact and
journal integrity, no-replay, and the inter-effect `HEALTHY` barrier still stop
or park work. Other host-only schema, shape, and evidence failures are H0 bugs
to fix and rerun, not new device-authority gates.

### Autonomy

| Tier | Rule |
|---|---|
| H0 | Unlimited. Rule 7 suspended. Fix and continue. |
| D0 | Autonomous for a resolved exact target. No approval. |
| D1 | Autonomous under the target presence mode. Only the qualified A90 resident lane may be unattended; all other D1 stays attended. |
| F1 | Autonomous while attended. No per-candidate approval. Rollback and health verification between attempts. At most one target may be F1-armed at a time. |

The agent owns goal selection, experiment design, and iteration. Do not require
a campaign-level planner or runner. Target runners are transaction primitives
for one device effect, durable intent, observation, recovery, and health.
Legacy v1 approval/time/action limits remain implementation constraints until
their runners change; they do not define the trial policy.

An F1 run parked while awaiting a required physical operator step remains
F1-armed. Host-only work continues during a park; no second candidate may be
armed, and a park is not an abort. Resume from durable journal state.

F1 exclusivity belongs to target-identity gate 1, not a fifth gate. H0/D0
preparation may coexist. A target becomes F1-armed when its journal durably
records candidate intent, before the first candidate effect, and remains armed
through observation, park, rollback, and recovery. Disarm only after exact
`HEALTHY` is durable; an uncontrolled or recovery-required close stays armed.

Each target contract defines its presence predicate. Only its qualified A90
resident D1 lane may be unattended; every F1 and all other D1 stay attended.

### Health, observation, and recovery

A missing, late, timed-out, or malformed observation is not by itself a device-health or recovery failure.
Endpoint absence is not target ambiguity; ambiguity requires multiple plausible targets or
conflicting bound identity. Unresolved observation freezes new effects as
`HEALTH_PENDING`, `HOST_OBSERVER_FAILURE`, or `RECOVERY_PENDING_PARKED`.

Until exact health and recovery establish `HEALTHY`, permit only passive bounded
observation, re-enumeration stabilization, H0 observer repair/replay, and exact
recovery. Never replay the uncertain action. A timeout parks rather than closes;
confirmed negative health enters recovery. Permanent stops and operator stop
still close. Attendance loss stops F1 and all D1 except the qualified A90 lane.

### Evidence

Routine narrative evidence is the commit body: attempt, result including no-proof, judgment, work, and a `Validation:` line.

Append the structured row to the per-target campaign ledger:
`docs/operations/CAMPAIGN_LEDGER_S22PLUS.md` or
`docs/operations/CAMPAIGN_LEDGER_A90.md`. Write a separate report only for a
new capability, a new hazard class, an incident, or a genuinely ambiguous
device-safety result. No per-run prose, no review ladder, and no per-candidate
policy document.

A superseded report moves to `docs/archive/reports/`; location is the authority signal.

---

This file contains the repository-wide invariants and the binding target
registry. Select exactly one target contract before target-specific work.
`GOAL.md` and `GOAL_A90.md` describe current state and objectives; they never
grant device authority. Historical or draft policies under `docs/archive/` or
elsewhere are evidence only, even if their text says `ACTIVE`.

The default work cycle is:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Do not add a device step when host-only work can answer the question.

## Authority and Precedence

The effective contract is, in descending order:

1. the common invariants in this file;
2. the selected binding target contract in the registry below;
3. the shared risk-tier and execution-process documents named by that target;
4. the immutable live binding required by the active policy or current runner.

The more restrictive applicable rule wins. A target contract may specialize
only behavior explicitly delegated by this file and may never relax the
permanent safety boundaries. A manifest, approval string, goal, report,
archived clause, helper string, or sub-goal cannot override a higher layer.

No document grants standing device authority unless this common contract or the
selected target contract expressly activates it and all required live inputs
are current. An unactivated policy edit remains H0 only.

## Binding Target Registry

| Target | Current state | Binding target contract | Binding live process |
|---|---|---|---|
| Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` / `S906NKSS7FYG8`) | `GOAL.md` | `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md` | `docs/operations/DEVICE_ACTION_PROCESS_V2.md` |
| Samsung Galaxy A90 5G | `GOAL_A90.md` | `docs/operations/targets/A90_TARGET_CONTRACT.md` | `docs/operations/targets/A90_TARGET_CONTRACT.md` sections `A90 D1 Resident Session`, `A90 F1 Resident Install`, and `Attended F1 Pre-Handoff` |

Targets, profiles, rollback identities, transports, approvals, and health
evidence never transfer between registry rows. If no binding target contract
matches the exact target and action, remain H0.

For A90 work, the required read order is this file, then
`docs/operations/targets/A90_TARGET_CONTRACT.md`, then `GOAL_A90.md`. The goal
records current state only and cannot grant or extend live authority.

## Permanent Device Safety Boundaries

1. Work only on an explicitly identified operator-owned device. Device effects
   require attendance except the exact A90 resident D1 lane delegated below;
   F1 is never unattended, and authority never transfers between targets.
2. The only partition payload permitted by the ordinary process is **boot**.
   Never write or flash recovery, vendor_boot, DTBO, vbmeta, vbmeta_system, BL,
   CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem,
   bootloader, or any other partition.
3. Never use raw host `dd`, fastboot, partition-table actions, qdl/Sahara/
   Firehose, RAM dump, EUD/UART writes, fuse/QFPROM actions, format operations,
   or an unreviewed panic/RDX path.
4. Never flash unless the exact rollback artifact is present, readable,
   hash-verified, and usable through a demonstrated recovery path.
5. Never flash a new experiment over an unhealthy or unverified device.
   Recover first, verify health, and stop that experiment.
6. A target ambiguity, unexpected archive member, forbidden partition signal,
   changed artifact, missing rollback, journal inconsistency, or lost physical
   recovery path is an immediate stop.
7. After an unexplained failure once a device or transfer session starts, stop
   the current experiment. The exact preauthorized rollback may resume only
   from durable journal state; candidate replay is forbidden. Any non-rollback
   continuation or retry must already be defined by the selected target
   contract and satisfy its predeclared proof conditions; otherwise stop.

## Permanent Repository and Evidence Boundaries

Do not commit firmware, boot images, ramdisks, compiled payloads, raw device
logs, credentials, device serials, PARTUUIDs, MAC/BSSID/IP values, KASLR
slides, or tunnel URLs. Keep private inputs and run evidence under
`workspace/private/`.

Changing a permanent device, repository, or evidence boundary is a separate
policy change and requires an independent safety review. A target contract
refactor must prove that these boundaries remain semantically unchanged.

## Proportional Device Actions

Classify every action using
`docs/operations/DEVICE_ACTION_RISK_TIERS.md` and the selected target contract:

- **H0:** host-only work. No device approval.
- **D0:** connected read-only work. Exact target and bounded reads.
- **D1:** transient no-payload control. Use active trial autonomy; outside the trial, require the selected target contract's fresh approval. A selected target contract may also define one separately reviewed, exact, rollback-recoverable storage-artifact cleanup sub-capability. That exception may remove only named target-owned files with exact host preservation and must not write a partition, configuration, credential, or security state.
- **F1:** a boot-only transfer process defined by the selected target contract.
- **X:** forbidden by the permanent boundaries.

Do not split a higher-risk action into lower-tier commands. A device-connected
action is not H0 merely because it sends no partition payload.

## Common F1 Invariants

The reusable ordinary F1 design is
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. Before approval, its runner must
prove the exact target/profile, regular candidate and rollback artifacts at
stable absolute paths, exact size and SHA256, permitted archive membership,
known healthy starting state, demonstrated physical recovery, a new durable
journal, and bounded observation/final-health requirements.

Outside the active trial, one fresh approval binds one candidate and recovery.
During the trial, policy adds no per-candidate approval, although a legacy
runner may still require its immutable compatibility binding. Once candidate
execution begins, rollback never waits. Candidate replay is forbidden.

Keep host rejection, local parser failure, device-session start, transfer
start/completion, observation, rollback, and final health distinct. A dry run
or pre-session host failure is not a candidate transfer, but any changed
execution-critical closure requires a new exact binding before live use.

Use ordinary absolute artifact paths. Do not pass `/proc/self/fd/*`, sealed
memfd paths, or runtime path-rebinding adapters to a transfer tool. Revalidate
the opened regular file after the tool returns.

F1 PASS requires both the intended bounded observation and the target-specific
healthy terminal state. Candidate boot or transfer success alone is not PASS.

## Evidence and Reporting

- Routine H0/D0/D1 work needs only the evidence required by its tier and target
  contract.
- Routine F1 output is one structured result, one append-only journal, private
  raw logs, and the target contract's canonical timeline.
- Write a prose report for a new capability, new hazard class, incident,
  ambiguous result, recovery deviation, or policy change.
- A reporting or parser failure after a proven transition must not cause that
  device transition to be repeated. Resume only from durable journal state.

## Review Rules

- One independent review is required when a common/target contract, F1 runner, schema, transfer/archive/recovery machinery, boundary, or hazard changes.
- Review changed execution-critical closure and higher-precedence interactions;
  ignore unreachable legacy helpers.
- An independent `PASS_GO` qualifies a capability, not a run. Reuse it across candidates,
  campaigns, manifests, qualifications, and ordinals while its named execution-critical hashes are unchanged and no new hazard or incident occurs. Fresh qualification and any runner binding still apply.
- Every new non-permanent gate must name the hazard or incident class it
  blocks, its scope, objective retirement evidence, and an expiry or review
  trigger. A gate without a retirement condition must be explicitly designated
  permanent and reviewed as a boundary; do not carry a temporary gate forward
  by default.

## Development and Commit Discipline

- Read this file, the selected target contract, and the target's current goal.
  Read both goals for a common or cross-target change. Inspect
  `git status --short` and keep edits scoped.
- Keep each active goal focused on current state and the selected bounded unit.
  Review completed history for archival above 800 lines; 900 lines is the hard
  limit for either goal file.
- Use canonical paths under `workspace/public/src/`, `workspace/private/`, and
  `docs/`. Do not recreate legacy root trees.
- Validate touched Python with `py_compile` and focused tests. Cross-compile
  touched C with the repository toolchain and inspect the output with `file`.
- Use scoped staging; never `git add -A` or `git add .`.
- Run `git diff --check` before commit. Commit only after the selected bounded
  unit is validated.
- Redact all private identifiers from tracked diffs.

## Stop and Escalate

Stop when evidence is ambiguous, a boundary would need to bend, recovery is
not available, or the current action is not represented by the selected tier
and target contract. Do not widen scope or retry-loop. Fall back to H0 analysis
and record the blocker.

Outside the active trial, pre-session host-only repair requires an explicit
target-contract rule; otherwise stop on the first material failure.
