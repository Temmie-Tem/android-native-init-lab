# AGENTS.md - repository operating contract

Contract-Revision: **2** (supersedes revision 1; 2026-08-03)

The retired Interim Fast-Loop trial contract is preserved byte-for-byte at `docs/archive/policy/AGENTS_INTERIM_FAST_LOOP_RETIRED_2026-08-03.md`; it is historical evidence only and grants no current authority.

---

This file contains the repository-wide invariants and the binding target registry.
Select exactly one target contract before target-specific work. A registry goal describes current state and objectives but never grants device authority.
Historical or draft policies under `docs/archive/` or elsewhere are evidence only, even if their text says `ACTIVE`.

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
| Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `G986NKSS8IYC2`) | `GOAL_S20PLUS.md` | `docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md` | Active exact-target routine D0/D1 including payload-free Download return; attended boot-only bootstrap and resident Magisk F1 active; reviewed attended native-canary R1 active |

Targets, profiles, rollback identities, transports, approvals, and health evidence never transfer between registry rows. Without an exact matching contract, remain H0.

For A90 work, read this file, then `docs/operations/targets/A90_TARGET_CONTRACT.md`, then `GOAL_A90.md`. The goal cannot grant or extend live authority.

## Permanent Device Safety Boundaries

1. Work only on an explicitly identified operator-owned device. Device effects
   require attendance except the exact A90 resident D1 lane and an exact S20+
   bounded autonomous-research lane separately activated by their binding
   target contracts. F1 is never unattended, and authority never transfers
   between targets.
2. The only partition payload permitted by the ordinary process is **boot**.
   Never send a partition image, raw block write, or flashing operation to
   recovery, vendor_boot, DTBO, vbmeta, vbmeta_system, BL, CP, CSC, super,
   userdata, persist, EFS, sec_efs, RPMB, keymaster, modem, bootloader, or any
   other partition. An exact reviewed D1 action performed through normal
   Android Package Manager or shared-user-storage APIs is an OS-mediated data
   write, not a partition payload; it is permitted only within the closed
   package/file staging rules below and never authorizes block or filesystem
   access to a partition mount outside that normal API.
3. Never use raw host `dd`, fastboot, partition-table actions, qdl/Sahara/
   Firehose, RAM dump, EUD/UART writes, fuse/QFPROM actions, format operations,
   or an unreviewed panic/RDX path.
   One narrow A90 boot-control exception may be activated by the A90 target
   contract: after an exact reviewed `boot` write and readback, the fixed TWRP
   System-reboot hook may clear exactly the first 256 bytes of `misc` BCB and
   nothing else before reboot. The hook path, complete bytes, size, SHA-256,
   TWRP version, recovery identity, ordering, and one-shot behavior must be
   fixed by reviewed code. It accepts no caller path, offset, count, command,
   or payload; drift or a second invocation stops. This exception grants no
   other `misc` access and never transfers to another target or process.
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
- **D0:** connected read-only work. Exact target and bounded reads. A binding
  target contract may additionally activate one independently reviewed,
  filename-grammar-bounded retrieval of an operator-created derived artifact
  from normal shared user storage into `workspace/private/`; it must enumerate
  only that closed artifact class, require exactly one match, publish host-side
  no-clobber, and compare device and host hashes.
- **D1:** attended non-partition control or an exact reviewed routine setup
  action. A current direct operator request authorizes one target-contract
  allowlisted invocation. Routine setup is limited to one pinned
  non-privileged Package Manager APK install or one pinned inert file staged
  no-clobber to shared user storage under
  `docs/operations/ROUTINE_CONNECTED_ACTIONS.md`. It never authorizes launch,
  patch, permission grants, arbitrary files/packages, partition payloads, or
  security/configuration changes. A selected target contract may also define
  the existing separately reviewed exact storage-artifact cleanup capability.
- **R1:** an attended exact privileged root-data transaction activated by one
  target contract outside D1/F1. It uses fixed no-input root commands for one
  pinned data-only payload in a finite surface, durable one-shot journal, and
  reviewed recovery owner. It grants no caller-supplied `su`, arbitrary module/
  path/configuration mutation, or partition payload; root grants no R1.
- **F1:** a boot-only transfer process defined by the selected target contract.
- **X:** forbidden by the permanent boundaries.

Do not split a higher-risk action into lower-tier commands. A device-connected
action is not H0 merely because it sends no partition payload.

## S20+ Bounded Autonomous Research Delegation
The S20+ target contract may activate one independently reviewed autonomous
research session without per-invocation attendance. It grants no authority
until the target section, exact runner, hostile tests, and execution-critical
identities receive independent `PASS_GO` and are mechanically activated.
The lane is exact `SM-G986N/y2q/y2qksx/G986NKSS8IYC2` only. Each session starts
with bounded public ADB inventory, requires one healthy match, binds hashed
serial/topology/current boot, and expires on disconnect, unowned reboot,
identity/build/source drift, unhealthy Android, foreign guard, or endpoint
ambiguity. Other rows receive zero commands.
Only reviewed named actions are selectable: bounded public D0 collection;
fixed no-input root-read-only profiles with complete commands, paths, node
types, bounds, and parsers; `reboot-system`; and a separately reviewed atomic
`download-roundtrip` choreography with its own guard/finalizer.
Callers supply no path, shell, property, service, executable, mount, credential,
or destination.
Root profiles may report only fixed bounded metadata, digests, and explicitly
parsed proc/sys text into `workspace/private/`; they extract no file bytes.
The lane forbids Odin payload/archive/partition transfer, F1 dispatch, root or Magisk/configuration
mutation, packages, shared-storage writes, mounts, deletion, permission,
property/service/security changes, and generic `su`.
Intent precedes each effect; uncertainty never replays. Entry/return intent is
one atomic no-replace node containing both child/campaign counter snapshots;
debit-only or partial-scope state grants nothing. Recovery requires a canonical
campaign/session/ordinal/source/endpoint/predecessor chain. Only the fixed
`/usr/bin/odin4 --reboot -d <bound-endpoint>` payload-free return may leave
Download. One attended opening creates a finite monotonic campaign. A reserved
return survives expiry only for bound arrival/return/final health and grants no
new baseline, entry, transaction, or capacity. Pre-F1 readiness stops before
F1 intent/entry/approval/transfer; F1/R1 remain freshly attended.

## Common R1 Invariants

R1 exists only for a target-contract-named persistent privileged-data experiment outside D1/F1. Its runner, schema, artifact closure, fixed commands, cleanup, recovery, and hostile tests require review before activation; capability PASS prepares no run or live authority.

One fresh attended approval binds the exact target/current boot, payload bytes, finite state/staging/module surface and inventory, root commands/reboots, cleanup, and recovery. The shared guard and intent-before-effect journal make each effect one-shot and retain the guard after uncertainty or malformed state. Strict typed JSON rejects duplicate keys, bool/integer substitution, indirect nodes, and raw-receipt mismatch. A post-intent write/fsync cut is `uncertain-consumed`: never replay it, but keep exact preauthorized recovery reachable. Callers select only named actions, never a path, shell fragment, ID, property, service, mount, credential, or executable.

An R1 journal final name exposes only complete file-fsynced bytes via atomic no-replace publication and directory fsync: before publication it is absent; afterward it is complete and parseable. Direct final-name writes are not durable R1 receipts.

Staging and installation are separate; staging intent is not a root-data attempt. Before install intent, exact prepared-only decline or same-target recovery may remove owned staged bytes and close with zero installs; install intent consumes the attempt without a result. Recovery revalidates only branch inputs and remains reachable without candidate build inputs. Before Magisk BusyBox use or disable-marker change it re-reads prepared Magisk and exact helper bytes. Stock AP remains required through transfer, but an exact completed-transfer health finalizer must not reopen it.

A privileged R1 sink must not reopen a payload from normal shared user storage. Stage it only in one fixed, exclusively claimed non-shared directory inaccessible to untrusted app UIDs; bind the direct non-symlink directory by owner, mode, and exact child set, and bind each direct regular payload by owner, mode, link count, exact size, and SHA-256 immediately before the sink. Directory link counts are filesystem-dependent and are not authority receipts. Concurrent independently authorized writers with the same staging UID are outside the lane and constitute an immediate stop. Ordinary, stock/root-absent, and abrupt-cut cleanup must remain available to that non-root staging owner and remove only bounded regular remnants at the fixed names without replaying installation.

Normal terminal requires bounded observation, one-shot replay proof, disablement, healthy exact-target return, and owned-stage cleanup. Each reboot rebinds its exact current source boot immediately before intent, and no returned observation may reuse the prepared or any earlier durable boot ID. Recovery never waits after an effect; Android-root recovery touches only the named disable marker. If exact rooted Android is unavailable, only separately reviewed stock recovery may consume a durable handoff and one prebound boot-only stock artifact; another F1 grants no authority. Physical Magisk Safe Mode is outside ordinary R1 because it can mutate Magisk database/configuration state in addition to module markers; a future target may authorize it only after separately binding and reviewing every such persistent side effect. Install, reboot, disable, cleanup, and stock transfer never replay after their durable intents.

Stock Download attribution requires an empty baseline, durable attended physical-action intent, and one exact bound arrival. The initial wait is finite. After an intent-only cut, a later invocation may observe the current sole exact endpoint once and publish arrival, but cannot repeat baseline or physical action. Legacy baseline-only, malformed arm/arrival, or a different endpoint grants no transfer. After rollback intent, missing/partial transfer results permit observation and recovery only, never Odin replay. Later exact root-absent health may close while retaining an unproved outcome; it cannot relabel completion or stock provenance.

Device one-shot evidence uses only the reviewed writer/parser's exact canonical bytes; semantic JSON equivalence, escaped fixed tokens, and out-of-range numbers are invalid. Cleanup may remove a bounded partial regular file only at its fixed owned staged name after staging intent; symlink, hardlink, special/oversized file, or extra namespace entry remains a stop.

Every host-reporting cut resumes without repeating a device effect. Durable branch terminal input, including stock health and transfer state, precedes cleanup. A finalizer may derive it from a complete journal, accept consumed partial cleanup only after read-only stage absence, publish a missing terminal, release a post-terminal guard, or re-emit an exact terminal after that guard was already released and only stdout was lost. A present foreign guard still rejects. Except for those terminal-only cuts, it repeats fresh target/root/branch reads; older health is not a standing lease.

R1 never weakens forbidden partitions, permits raw block access, or makes root general maintenance authority. Target/build, Magisk, payload, namespace, command/schema, recovery artifact/transport, or health-model drift expires it.

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

- Read this file, the selected target contract, and every affected goal; inspect
  `git status --short` and keep edits scoped.
- Keep each active goal focused on current state and the selected bounded unit.
  Review completed history for archival above 800 lines; 900 lines is the hard
  limit for any goal file.
- Use canonical paths under `workspace/public/src/`, `workspace/private/`, and
  `docs/`. Do not recreate legacy root trees.
- Validate touched Python with `py_compile` and focused tests. Cross-compile
  touched C with the repository toolchain and inspect the output with `file`.
- Use scoped staging; never `git add -A` or `git add .`.
- Run `git diff --check` before commit. Commit only after the selected bounded
  unit is validated.
- Redact all private identifiers from tracked diffs.

## Stop and Escalate

Stop when evidence is ambiguous, a boundary would need to bend, recovery is not available, or the current action is not represented by the selected tier and target contract.
Do not widen scope or retry-loop. Fall back to H0 analysis and record the blocker.

Outside the active trial, pre-session host-only repair requires an explicit target-contract rule; otherwise stop on the first material failure.
