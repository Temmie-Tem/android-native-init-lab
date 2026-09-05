# AGENTS.md - repository operating contract

Contract-Revision: **9** (supersedes revision 8; 2026-09-05)

The retired Interim Fast-Loop trial contract is preserved byte-for-byte at `docs/archive/policy/AGENTS_INTERIM_FAST_LOOP_RETIRED_2026-08-03.md`; it is historical evidence only and grants no current authority.

This file contains the repository-wide invariants and the binding target registry.
Select exactly one target contract before target-specific work. A goal records
current state and objectives; it never grants device authority.
Historical or draft policies under `docs/archive/` or elsewhere are evidence only, even if their text says `ACTIVE`.

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Do not add a device step when host-only work can answer the question.

## Authority and Precedence

The effective contract is, in descending order:

1. this file and its incorporated [common device details](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md), at the same highest common-contract precedence;
2. the selected binding target contract;
3. the shared risk-tier and execution-process documents named by that target;
4. the immutable live binding required by the active policy or current runner.

The more restrictive applicable rule wins. A target may specialize only
expressly delegated behavior and may never relax permanent boundaries.
A manifest, approval string, goal, report, archived clause, helper string, or
sub-goal cannot override a higher layer. No document grants standing device
authority unless this common contract or the selected target contract expressly
activates it and all required live inputs are current. An unactivated policy
edit remains H0 only.

The incorporated details have SHA-256:
`63441fe10cd9df4aa65958ae6de047819a1b1f1e17f4ffc1afafd03b55a91c4e`.
Verify that digest with existing hash tooling when first reading details for a
device action, or after their bytes change; reuse the verified unchanged input.
A missing, unread applicable section or mismatched digest blocks that device
effect, while H0 work may continue. Changes to the details must update this root
pin, so existing runners that bind AGENTS.md also bind their declared identity.
This refactor does not repin existing approvals, source closures, manifests,
activation records, or journals. Current runner checks and device-session stops
remain binding; change those mechanisms only through their scoped review.

## Default Research Autonomy

Within the operator-authorized research task, proceed autonomously with H0 and
with already activated, scope-matching device capabilities. Do not ask the
operator to repeat authorization or visually confirm a fact that the approved
machine observer can establish. A fresh target/boot/artifact binding is a
machine check, not by itself a request for fresh human approval. Reuse a valid
capability review and an unexpired in-scope session grant; do not ask again at
each internal read, observation, or already authorized recovery step.

Keep four questions separate: what work the operator authorized; whether the
operator must be physically present; whether current runtime binding passes;
and what recovery is actually available. Machine-verifiable observation,
safe stopping without another effect, and demonstrated automatic recovery are
different properties. A normal reboot's changed boot ID and healthy return do
not prove recovery if the experimental component stops responding.

H0 needs no device permission. A target may expressly bind named fixed D0
profiles to the current foreground research task without per-read requests or
physical attendance. For device effects, use the existing activated lane and
its limits: continue autonomously where it delegates that authority; otherwise
complete the smallest necessary H0 implementation/review/activation work first.
Prefer reusable reviewed capabilities over experiment-by-experiment approval
ceremonies. Do not introduce new gates or orchestration only to restate consent.

Request operator input only for missing information or authority that matters:
a scope-changing persistent mutation, unavailable or uncertain recovery, an
unresolved device-session stop, a required physical action, or an explicit
lane-specific fresh approval/attendance requirement. Identify the applicable
clause and missing condition; do not invent a generic screen-confirmation gate.
The default does not waive boundary 1, activate dormant runners, renew budgets,
transfer authority between targets, consume a new effect after uncertainty, or
turn a possible rollback into an authorized and demonstrated recovery route.

## Binding Target Registry

| Target | Current state | Binding target contract | Live process |
| --- | --- | --- | --- |
| Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` / `S906NKSS7FYG8`) | [GOAL.md](GOAL.md) | [S22+ contract](docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md) | [Process v2](docs/operations/DEVICE_ACTION_PROCESS_V2.md) |
| Samsung Galaxy A90 5G | [GOAL_A90.md](GOAL_A90.md) | [A90 contract](docs/operations/targets/A90_TARGET_CONTRACT.md) | Target sections `A90 D1 Resident Session`, `A90 F1 Resident Install`, `Attended F1 Pre-Handoff` |
| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) | `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` | Active exact-target routine D0/D1 including payload-free Download return; classic-fastboot census ordinals 1/2 consumed, with ordinal 2 four-query PASS and healthy return; fastboot-boot support F1 consumed with NO_PROOF healthy return; retained-T2 TWRP-fastbootd census consumed and first staged preparation probe consumed with NO_PROOF healthy return; staged fastbootd preparation Q1 consumed with PASS healthy return; TWRP-fastbootd census Q2 consumed with NO_PROOF healthy return; attended fixed root-health D0 active; attended boot-only bootstrap, resident Magisk, and recovery-canary B0 F1 active; recovery-canary T0 and TWRP T1 F2 candidates consumed; TWRP T2 recovery retained and candidate consumed; reviewed attended native-canary R1 active; PMSG warm-reboot marker D1 V1 activated, consumed and closed `NO_PROOF` healthy with its trial path retired, V2 dormant pending fresh review |

Targets, profiles, rollback identities, transports, approvals, and health
evidence never transfer between rows. Without an exact matching contract,
remain H0. For A90, read this file, its target contract, then GOAL_A90.md.

## Permanent Device Safety Boundaries

These numbered summaries preserve the boundary references used by existing
contracts. Their complete wording and closed exceptions remain binding in
[Permanent Device Safety Boundaries](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md#permanent-device-safety-boundaries).
Read an exception's complete conditions before considering it applicable.

1. Use only an explicitly identified operator-owned device. Device effects are
   attended unless the common contract expressly delegates an exception and
   the exact target has activated it. Normal control, safe stopping, automatic
   recovery and physical attendance are separate requirements.
2. Ordinary partition payloads are **boot only**. Recovery, vendor_boot, DTBO,
   vbmeta/vbmeta_system, BL/CP/CSC, super, userdata, persist, EFS/sec_efs, RPMB,
   keymaster, modem, bootloader and other partitions remain forbidden outside
   the exact retained S20+ T0/T1/T2 recovery exceptions. Normal Android API
   staging is limited to the separately defined package/shared-storage rules.
3. No raw host `dd`, arbitrary fastboot, partition-table actions,
   qdl/Sahara/Firehose, RAM dump, EUD/UART writes, fuse/QFPROM actions, format,
   or unreviewed panic/RDX. Only the exact S20+ fastboot exceptions and A90
   fixed 256-byte misc-BCB hook in the details can specialize these bans.
4. Before flashing, require the present, readable, hash-verified exact rollback
   artifact and a demonstrated usable recovery path. The S20+ recovery-only
   exceptions retain their exact stock-digest and physical-return conditions.
5. Never flash a new experiment over an unhealthy or unverified device.
   Recover first, verify health, and stop that experiment.
6. Target ambiguity, unexpected archive members, forbidden partition signals,
   changed artifacts, missing rollback, inconsistent journals, or lost physical
   recovery immediately stop new device effects.
7. An unexplained device/session/transfer failure stops the experiment.
   Preauthorized rollback resumes only from durable journal state;
   candidate replay is forbidden. Any other continuation must already be
   defined by the target contract and satisfy its predeclared proof conditions.

## Permanent Repository and Evidence Boundaries

Do not commit firmware, boot images, ramdisks, compiled payloads, raw device
logs, credentials, device serials, PARTUUIDs, MAC/BSSID/IP values, KASLR
slides, or tunnel URLs. Keep private inputs and run evidence under
`workspace/private/`.

Changing a permanent device, repository, or evidence boundary is a separate
policy change and requires an independent safety review. A target contract
refactor must prove that these boundaries remain semantically unchanged.

## Proportional Device Actions

Use the selected target and [risk tiers](docs/operations/DEVICE_ACTION_RISK_TIERS.md).
The complete tier definitions and exact delegations are in the incorporated
details; this routing table neither changes their scope nor activates a lane.

| Work | Required detail when applicable |
| --- | --- |
| H0 host analysis/build/tests/docs | Root development rules; selected target/goal for target-specific work. Do not load unrelated live protocols. |
| D0 bounded connected reads or D1 control | [Proportional Device Actions](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md#proportional-device-actions) and the target's named profile; read any invoked permanent-boundary exception. |
| Reusable unattended D1 | [Bounded Machine-Controlled D1](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md#bounded-machine-controlled-d1); target activation, finite grant, safe-stop or demonstrated recovery evidence. |
| S20+ autonomous research | [S20+ delegation](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md#s20-bounded-autonomous-research-delegation); its separate limits and attendance rules. |
| S20+ PMSG ordinary-reboot transaction | `S20PLUS_PMSG_WARM_REBOOT_D1_DELEGATION_V1` in the D1 definition; single transaction, not a reusable autonomous session. |
| R1 persistent privileged-data experiment | [Common R1 Invariants](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md#common-r1-invariants) and its exact target lane. |
| F1 boot-only transfer | [Common F1 Invariants](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md#common-f1-invariants), Process v2 and the selected target's actual process. |
| Conditional unattended F1 | [Conditional Autonomous F1](docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md#conditional-autonomous-f1); actual failure-specific automatic recovery is required. |
| F2/T1/T2 or fastboot exception | Complete permanent-boundary exception and tier/target conditions; consumed actions remain consumed. |
| X | Forbidden; remain H0. |

Do not split a higher-risk action into lower-tier commands. A device-connected
action is not H0 merely because it sends no partition payload. Required reads
are scoped to the current action and reusable while their inputs are unchanged.

## Evidence and Reporting

- Routine H0/D0/D1 work needs only the evidence required by its tier and target
  contract.
- Routine R1 output is one exact private run, append-only one-shot intents and
  results, bounded private raw command evidence, and one terminal structured
  result. A new R1 capability, recovery deviation, or incident also requires a
  prose report.
- Routine F1 output is one structured result, one append-only journal, private
  raw logs, and the target contract's canonical timeline.
- Write a prose report for a new capability, new hazard class, incident,
  ambiguous result, recovery deviation, or policy change.
- A reporting or parser failure after a proven transition must not cause that
  device transition to be repeated. Resume only from durable journal state.
- Preserve bounded raw failure evidence before result interpretation can fail,
  within the selected target's existing capture/privacy rules; this does not
  expand permitted raw collection or replace a digest-only evidence boundary.
  Record the source version and evidence location in the existing close record
  so later audit does not depend on the moving working tree. Routine narrative
  may be a concise commit body; do not duplicate it across per-run documents.

## Review Rules

- One independent review is required when a common/target contract, F1 runner, schema, transfer/archive/recovery machinery, boundary, or hazard changes.
- Review changed execution-critical closure and higher-precedence interactions;
  ignore unreachable legacy helpers.
- An independent `PASS_GO` qualifies a capability, not a run. Reuse it across candidates,
  campaigns, manifests, qualifications, and ordinals while its named execution-critical hashes are unchanged and no new hazard or incident occurs. Fresh qualification and any runner binding still apply.
- Scope review to reachable execution and the stated threat model in
  `docs/operations/DEVICE_ACTION_RISK_TIERS.md`. Out-of-model speculation does
  not automatically create mandatory machinery. A concrete new hazard stops
  the affected scope and changes that review scope. Do not reopen resolved
  work without changed inputs or new evidence.
- Track whether old findings affect the current path, are explicitly covered,
  or belong to a retired path. Different-topic PASS is not automatic coverage;
  unrelated historical pending counts are not a blanket gate on new work.
- Every new non-permanent gate must name the hazard or incident class it
  blocks, its scope, objective retirement evidence, and an expiry or review
  trigger. A gate without a retirement condition must be explicitly designated
  permanent and reviewed as a boundary; do not carry a temporary gate forward
  by default.

## Development and Commit Discipline

- Read this file, the selected target contract, and every affected goal; inspect
  `git status --short` and keep edits scoped.
- Keep each active goal focused on current state and the selected bounded unit.
  Review completed history for archival above 800 lines; 900 lines is the hard
  limit for any goal file.
- Use canonical paths under `workspace/public/src/`, `workspace/private/`, and
  `docs/`. Do not recreate legacy root trees.
- State the bounded task and completion criterion briefly. Read current bytes
  and the actual consumer before diagnosing a past incident; consult history
  when generation or cause is uncertain, not before every unchanged read.
- For the selected goal, prioritize the smallest useful working capability
  within existing safety and proof requirements. Keep functional evidence
  independent from detailed causal analysis and optional diagnostics; do not
  gate that capability on their completion unless needed for safe execution
  or its stated success criterion.
- Before an expensive build or device experiment, use already available
  evidence and existing low-cost checks to resolve questions they can answer.
- Prefer the smallest working change and existing tools. Avoid speculative
  frameworks and candidate-specific copies; derive repeated registration,
  encoding and result rules from one existing declaration where practical.
  New daemons/proxies must justify their in-scope benefit and must not break
  the existing transport or recovery through resource contention.
- Validate touched Python with `py_compile` and focused tests. Cross-compile
  touched C with the repository toolchain and inspect the output with `file`.
  Exercise representative real producer/consumer and failure paths, not just
  unrelated helpers. Use fixed fixtures and behavioral invariants; do not pin
  growing ledger counts or the checkout's current activation state as answers.
  Historical snapshot tests must bind their historical input.
- Reuse successful checks and build outputs while their relevant inputs are
  unchanged. Expand validation only for changed paths, failures or new evidence.
  Documentation-only changes need content/link/diff checks, not image builds;
  a contract's semantic change still needs review. Unrelated census counts and
  other-target changes should not be execution identity. Remove accidental
  bindings through reviewed code changes, never by bypassing current checks.
- Keep prepare, activation, consumption, recovery and terminal prerequisites
  distinct. A stage must not invalidate itself by creating its normal output;
  recovery must not rerun a pre-consumption absence check. Actual target,
  artifact, authority and no-replay checks remain mandatory at the effect.
- Stop expanding a task once its completion criterion and relevant checks pass.
  Put necessary validation rationale in the existing change description rather
  than adding a separate approval or evidence layer for every correction.
- Use scoped staging; never `git add -A` or `git add .`.
- Run `git diff --check` before commit. Commit only after the selected bounded
  unit is validated.
- Redact all private identifiers from tracked diffs.

## Stop and Escalate

Stop new device effects when target, effect occurrence, health, authority or
recovery is uncertain, a boundary would need to bend, or the action is not
represented by the selected tier and target contract. Preserve the journal;
continue only allowed observation, H0 diagnosis and preauthorized recovery.
An expected negative or unproved research result is not itself a safety fault;
any next experiment still requires a closed run, exact health and its own
current authority. Unexplained device-session failures retain boundary 7.

H0 build, parser and test failures may be repaired and rechecked within the
same authorized task without a new approval or a fixed failure-count stop.
Stop an approach when it repeats without new evidence, exhausts its resource
budget, or needs a scope change. This replaces blanket first-failure and
one-repair H0 rules; it never permits replay of a device effect, editing a
consumed journal, relaxing a safety assertion to obtain PASS, or ignoring an
explicitly narrower operator instruction.
