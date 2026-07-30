# AGENTS.md - active operating contract

This is the binding contract for agents working in this repository. `GOAL.md`
defines the current objective. Historical policies under `docs/archive/` are
evidence only and grant no device authority, even if their text says `ACTIVE`.

The default work cycle is:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Do not add a device step when host-only work can answer the question.

## Current Live Posture

- No S22+ F1 live run is currently authorized.
- No A90 F1 live run is currently authorized. A90 run
  `a90-debian-reactivation-f1-20260730-01` consumed its exact approval.
  V3402 candidate and exact V2321 rollback each completed one checked boot-only
  transfer with no candidate replay. The transaction is `CLOSED` with verdict
  `NO_PROOF_DEBIAN_HANDOFF_CANDIDATE_ROLLED_BACK` and final V2321 health
  restored.
- A90's first SD-backed Debian handoff validated the bound rootfs SHA, attached
  the loop, mounted ext4, and validated `/sbin/init`, then stopped before
  `switch_root` at display-owner cleanup `-EBUSY`. That rw mount/unmount changed
  the rootfs image bytes. The one bounded corrected handoff stopped at the
  immutable SHA gate before mount. Debian PID1 was not reached, internal
  userdata was not touched, and the changed rootfs was not accepted.
- The selected A90 successor is H0-only: move display-owner cleanup before loop
  attachment/rw mount, preserve a fresh immutable SD rootfs input for each
  attempt, and make every pre-`switch_root` failure leave that input
  byte-identical. Do not replay V3402 or seek live authority until a fresh
  versioned candidate, static validation, exact rollback, and new approval
  exist.
- P2.82 consumed one exact approval. Its byte-identical reads end in terminal
  failure `0x8e/detail=0xc10`; the newline-bearing comparator made exact NONE
  readback impossible. No accepted ACM endpoint appeared. Child suspend,
  DEVICE restart, child PHY reinitialization, configfs UDC bind, final bus
  sampling, and host ACM receipt were not reached. Rollback/final health passed
  and the transaction is `CLOSED`.
- P2.84 supersedes P2.82 for new-candidate selection. Run
  `023060c8dd0ab036f8547a816624356f` passed `20/20` pre-LTO, Full-LTO A/B,
  linked/package/static closure, and offline promotion. P2.82 remains
  historical evidence only.
- P2.84 then consumed one exact approval. Candidate and exact rollback each
  completed one boot-only transfer with no replay; the transaction closed
  `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` with final health restored.
- Retained `0x8e/detail=0` proves normalized NONE readback and inner
  `dwc3_otg_start_peripheral(..., 0)` return. Retained `0x8f/detail=0xc18`
  proves child suspend and the zero-return PHY power helper nested in that
  helper; it does not prove analog change. No `0x90` or later checkpoint
  survived, so DEVICE restart and all later E3/ACM boundaries remain unproved.
- The restart helper has an unclosed deadline: after `SIGKILL` it blocks in
  `wait4`. Both retained slots staying CRC-valid proves no generation-89 write
  reached its first durable CRC clear.
- Exact source rejects the same-queue `perf_vote_work` deadlock. Outer SM work
  uses `k_sm_usb`; perf work uses `system_wq`.
- Both stock-D1 approvals are consumed. V2 registered all 27 probes, executed
  one control NONE/restore pair and no challenge, then returned healthy. Its
  false timeout came from trace spelling and two watchdog-disarm waits.
- Raw-trace correction: on stock, the first two outer invocations returned by
  `0.291 ms`; child and parent suspend callbacks then ran asynchronously on
  `kworker/0:*`, with parent `dwc3_msm_suspend` at
  `17.873..19.504 ms`. Thus the first-outer-return window and a generic outer
  fence are not the load-bearing PM boundary.
- This stock ordering does not transfer unchanged to bare PID1. P2.84's
  accepted `0xc18` required the child suspend and PHY power-off pairs to use
  the stop-helper PID and be nested inside
  `dwc3_otg_start_peripheral(..., 0)`. PM reference/child-count state selected
  different stock and bare execution.
- The selected successor gate is H0-only: after exact child `suspended`, wait
  on the same deadline for exact parent `runtime_status=suspended` before any
  PERIPHERAL write. Parent success implies the callback returned and
  `suspend_resume_mutex` was released; a callback wedge must time out before
  the write. It does not prove outer-work return: requeue bookkeeping and the
  worker tail remain. Keep actual outer entry/return probes and a bounded,
  classified PERIPHERAL-write helper. No kernel change is required.
- Implement that gate only in a fresh versioned source contract and run ID.
  P2.84 lacks the parent path and failure semantic, so this is not an in-place
  one-line patch. Also repair the generic blocking-`wait4` helper deadline and
  fault-test it. No new stock D1 is required before that H0 implementation.
- P2.86 Stage A change closure is frozen before intent: 60 P2.84 SOURCE_KEYS
  are inherited byte-for-byte and only 10 byte-affecting overlays join them
  (`70` total). Ten verifier/evidence support files stay outside SOURCE_KEYS
  and are later bound by `bundle.sha256`. Git-derived tracked changes since
  the frozen base must equal their declaration in both directions. Four D1
  repairs remain private and disjoint. Intent/build stay forbidden until all
  frozen files exist and the pre-intent gate passes. P2.64 Stage C is deferred
  until after P2.86.
- Do not repeat P2.82, replay or rebuild P2.84, or seek live authority during
  this H0 unit. `persist.adb.tcp.port` remains forbidden.
- Every new S22+ USB trace contract must pass the attachment-name gate with
  zero issues; frozen P2.82/P2.84 remain historical mismatches, not exceptions
  reusable by a new candidate.

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
- Keep `GOAL.md` near a 500-700 line working target. Review completed history
  for archival above 800 lines; 900 lines is the hard limit.
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
