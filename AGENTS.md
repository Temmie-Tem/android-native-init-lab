# AGENTS.md - active operating contract

This is the binding contract for agents working in this repository. `GOAL.md`
defines the current objective. Historical policies under `docs/archive/` are
evidence only and grant no device authority, even if their text says `ACTIVE`.

The default work cycle is:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Do not add a device step when host-only work can answer the question.

## Current Live Posture

- No S22+ F1 live run is currently authorized.
- P2.54 has one exact host-qualified proof-bound SSUSB classifier candidate.
  P2.55 fixed the downstream versioned reachable-record verifier without
  changing the kernel, userspace, boot image, candidate AP, or rollback AP.
- The first P2.55 connected D0 stopped read-only on a historical retained
  family. It created no prepared binding, transaction, Odin session, or
  transfer.
- One operator-preapproved normal Android reboot ran exactly once. The target
  disconnected and reconnected, but the D1 recorder rejected an empty
  early-boot `sys.boot_completed` value before completing its timeline. No
  second reboot ran. A private incident record preserves that reporting
  deviation, and the fresh D0 below independently proves final health.
- The second P2.55 connected D0 passed exact target, Android/FYG8/root/boot
  health, rollback, candidate, clean retained baseline, Odin absence, and the
  current execution closure. Its private prepared binding reopens cleanly and
  has no transaction. It is unconsumed but grants no F1 authority.
- The operator's standing approval explicitly excludes a new-build flash.
  Only the exact fresh token from that prepared binding can authorize one
  candidate attempt and its mandatory rollback. Do not place that token in
  tracked files.

## Permanent Safety Boundaries

1. Work only on an explicitly identified device owned and attended by the
   operator. Evidence and authorization never transfer between targets.
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
7. An unexplained failure after an Odin/device session starts is an immediate
   stop. The same material host-side or pre-session failure twice also stops the
   line of work. This stops candidate experimentation; it does not cancel the
   already-authorized exact rollback path. Rollback recovery may resume only
   from durable journal state and must never retry the candidate.
8. Do not commit firmware, boot images, ramdisks, compiled payloads, raw device
   logs, credentials, device serials, PARTUUIDs, MAC/BSSID/IP values, KASLR
   slides, or tunnel URLs. Keep private inputs and run evidence under
   `workspace/private/`.

Changing these boundaries is a separate policy change. An experiment manifest,
operator acknowledgement, archived clause, helper string, or sub-goal cannot
override them.

## Proportional Device Actions

Classify every action using
`docs/operations/DEVICE_ACTION_RISK_TIERS.md`:

- **H0:** host-only work. No device approval.
- **D0:** connected read-only work. Unambiguous target and bounded reads.
- **D1:** transient no-payload control. One fresh approval, bounded exact
  command, and return-health check.
- **F1:** one boot-only candidate transfer plus its mandatory rollback under
  Process v2.
- **X:** forbidden by the permanent boundaries.

Do not split a higher-risk action into lower-tier commands. D0 and ordinary D1
do not require a bespoke policy, one-shot state, model-review ladder, or prose
report.

## F1 Process v2

The canonical design is
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. F1 uses one reusable runner and
an immutable candidate manifest. Candidate-specific live helpers and policy
activation commits are retired as an execution model.

Before approval, the runner must prove:

- one exact target and target profile;
- a regular-file candidate AP and rollback AP at stable absolute paths;
- exact size and SHA256 for execution-critical artifacts;
- exactly one regular AP member named `boot.img.lz4` in each AP;
- no forbidden member or slot;
- a known healthy starting state and demonstrated physical Download recovery;
- an empty/new durable run journal; and
- bounded observation and final-health requirements from the manifest.

One fresh approval binds the target, candidate hash, rollback hash, manifest
hash, and runner version. It authorizes one candidate attempt and the necessary
rollback. Once candidate execution begins, rollback is already authorized and
must never wait for another acknowledgement.

The durable state machine is:

`PREFLIGHT -> APPROVED -> DOWNLOAD_IDENTIFIED -> CANDIDATE_FLASHED -> OBSERVED -> RECOVERY_DOWNLOAD -> ROLLBACK_FLASHED -> HEALTH_VERIFIED -> CLOSED|ABORTED`

Record a journal entry before invoking Odin and after every transition. Keep
host rejection, Odin local-parse failure, endpoint discovery, device-session
start, transfer start/completion, rollback, and final health distinct. A dry
run or pre-session host failure is recorded but is not a permanent one-shot
consumption. Any later candidate attempt still requires a new approval.

Use ordinary absolute `.tar.md5` paths. Do not pass `/proc/self/fd/*`, sealed
memfd paths, or runtime path-rebinding adapters to Odin. Revalidate the opened
regular file after Odin returns.

F1 PASS requires both the intended bounded observation and verified rollback to
the known healthy state. Candidate boot or Odin success alone is not PASS.

## Evidence and Reporting

- Routine H0/D0/D1 work needs only the evidence required by its tier.
- Routine F1 output is one structured result, one append-only journal, raw tool
  logs in private storage, and a timeline with only:
  `events:[{name,timestamp_utc}]`.
- The canonical F1 event order is `live_session_start`,
  `candidate_flash_start`, `candidate_flash_done`, `candidate_boot_ready`,
  `rollback_flash_start`, `rollback_flash_done`, `rollback_boot_ready`, and
  `live_session_end`.
- Write a prose report only for a new capability, new hazard class, incident,
  ambiguous result, recovery deviation, or policy change.
- A reporting or parser failure after a proven transition must not cause that
  device transition to be repeated. Resume from the durable journal.

## Review Rules

- One independent safety review is required when the F1 runner, manifest
  schema, Odin wrapper, archive verifier, recovery logic, permanent boundary,
  or a hazard class changes.
- Re-review only the changed execution-critical closure. Do not hash or review
  unreachable legacy helpers.
- A new candidate with unchanged machinery requires fresh preflight and
  approval, not another multi-review ladder.

## Target Notes

- S22+ FYG8 full-stock evidence is defined by
  `docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`.
  It is recovery evidence only and never authorizes full-firmware, BL, CP, CSC,
  userdata, or non-boot flashing.
- A90 and S22+ use separate target profiles, rollback identities, transports,
  and health checks. Never reuse one target's proof for the other.
- A90's existing checked flash path remains `native_init_flash.py` until it is
  migrated deliberately. S22+ F1 uses Odin with a regular boot-only AP.

## Development and Commit Discipline

- Read `GOAL.md`, inspect `git status --short`, and keep edits scoped.
- Use canonical paths under `workspace/public/src/`, `workspace/private/`, and
  `docs/`. Do not recreate legacy root trees.
- Validate touched Python with `py_compile` and focused tests. Cross-compile
  touched C with the repository toolchain and inspect the output with `file`.
- Use scoped staging; never `git add -A` or `git add .`.
- Run `git diff --check` before commit. Commit only after the selected bounded
  unit is validated.
- Redact all private identifiers from tracked diffs.

## Stop and Escalate

Stop when evidence is ambiguous, a boundary would need to bend, recovery is not
available, or the current action is not represented by the selected tier. Do
not widen scope or retry-loop. Fall back to H0 analysis and record the blocker.
