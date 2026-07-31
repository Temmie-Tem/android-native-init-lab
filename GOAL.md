# Goal: repeatable multi-device native PID 1

Build a repeatable path from an Android vendor boot chain and source-matched
vendor kernel to a custom static `/init` running as PID 1, then grow that entry
point into a minimal observable and recoverable Linux-style runtime.

Current targets are Galaxy A90 5G and Galaxy S22+. Target evidence, artifacts,
and authorization are isolated. `AGENTS.md` is the binding operating contract.

## Current Frontier

**State: direct PID1, E1A/E1B, E2 through the real UDC, and E3 through exact
configfs UDC binding are live proven. P2.90 F1 is closed healthy/no-proof.
P2.84, P2.86, P2.88, and P2.90 each ended with the same CRC-valid active
`generation=88/stage=0x8f/outcome=PROGRESS/item=0/detail=0xc18`; each candidate
and exact Magisk rollback completed once, with no replay and verified final
health.**

Candidate-bound native replay now proves why no later checkpoint survived.
The inherited kernel state stores generation/stage/item but not outcome/detail.
Before the next write it reconstructs the active slot as `PROGRESS/detail=0`,
mismatches committed `detail=0xc18`, and returns pre-mutation `-ESTALE`.
Userspace discards that errno and intentionally enters `quiet_park()`. There is
no unexplained syscall hang at this boundary, and the earlier USB/PM/tracefs/
publisher-nonreturn attributions are superseded.

The four formal Process-v2 verdicts remain
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`: rollback and health evidence are
unchanged, while restart-helper dispatch and every later E3 boundary remain
unproved. This is observation-channel recovery, not E3 progress. The next
successor must repair and exhaustively prove `ACCEPT_TO_RESUME_CLOSURE`, its
full 107-position walk, separate checkpoint-errno observability, and P2.64
Stage C `CHECKPOINT_SOT_COHERENCE` before Full-LTO, manifest, D0, or another F1.

The live transaction exercised the durable recovery design. Initial rollback
endpoint discovery stopped on a measured USB membership race. Rollback-only
recovery transferred the exact rollback once, durably reached
`ROLLBACK_FLASHED`, then met the known post-transfer USBFS departure race. A
final recovery performed no transfer and closed final health. Candidate and
rollback counts are exactly one each; there was no replay or retransmission.

**A90 parallel state: the V3402 run remains closed healthy/no-proof and
non-replayable. Its late display cleanup consumed the old rootfs identity.
The host-only V3403 successor now cleans all display owners before storage,
mounts only an absent-only work copy, and proves every modeled pre-switch
failure leaves the source byte-identical. V3403 passes the focused `41/41`
suite and AArch64 compile. A fresh, package-authenticated, clean 2 GiB D3
sysvinit rootfs and the exact V2321 rollback are hash-verified. A host-only
absent-only SD staging adapter now uses an exclusive ext4 directory and
hard-link no-clobber publication. The first independent review correctly
returned `NO_GO`: normal flashes did not pin recovery ADB, both boot helpers
used a nonexistent combined marker, one journal/timeline gap blocked recovery,
the stage-path D0 was circular and semantically weak, stale staging could be
reused without a candidate-time remote hash, and the tracked closure contained
a concrete device address. The host-only remediation now derives the stage
path from stable run ID, semantically validates D0, reconstructs the exact
private recovery target for every boot transfer, separates version/build
checks, repairs timelines from durable journal state, refuses preexisting
staging output, and rehashes the remote rootfs immediately before candidate
intent. The second independent review correctly returned `NO_GO`: the draft
manifest could self-declare authority without a fresh operator approval
receipt, staging results could be created as mode `0664`, journal final names
were exposed before a complete durable write, and subprocess timeout/exec
errors escaped without structured phase evidence or a guaranteed-private raw
log. The second host-only remediation keeps all manifest authority false,
separates approval preparation from execution with one exact private token,
publishes result/journal JSON only after a complete mode-`0600` write and
`fsync`, and classifies timeout/exec failures into private raw-log records.
The third independent review correctly returned `NO_GO`: an unmarked candidate
helper timeout was misclassified as definite pre-session rejection and dropped
rollback authority, while a rollback helper pre-spawn error consumed the only
rollback attempt even though no process had started. The third host-only
remediation treats timeout as candidate-state uncertainty with mandatory
rollback, and records an exact `process-spawn` failure as transfer count zero
so rollback-only recovery can resume under the consumed approval. Any
possibly-started rollback remains non-retryable. The fourth independent review
correctly returned `NO_GO`: a malformed process-not-started record appended
after a started failure could satisfy the loose retry predicate. The fourth
host-only remediation accepts only one directly adjacent latest
intent/process-not-started pair with exact outer/nested shape, zero-transfer
fields, recovery mode, private empty raw-log path/size/SHA, and prior rejection
count. The fifth independent review correctly returned `NO_GO`: Python numeric
type equivalence, arbitrary `*Error` strings, noncanonical timestamps, and a
resolve-before-lstat raw-log check still admitted malformed evidence. The
fifth host-only remediation requires exact integer types and canonical
timestamps, normalizes spawn failures to exact `OSError`, and rejects the exact
raw-log pathname as a symlink before resolution. The sixth independent review
correctly returned `NO_GO`: resolving the expected pathname still allowed a
symlink target to redefine the journal value, and an older possibly-started
rollback remained hidden behind a later exact pair. The sixth host-only
remediation keeps the expected lexical leaf unresolved through its `lstat`
check and requires the complete rollback-history suffix to consist only of
exact adjacent pre-spawn pairs with one recovery mode and unique ordinal log
names. The seventh independent review correctly returned `NO_GO`: distinct
expected names could still hardlink one empty inode, and a renamed historical
record retaining only nested `process_started=true` escaped top-level suffix
discovery. The seventh host-only remediation requires every retry log to have
one link and treats any nested process-start marker as rollback-related unless
the complete outer record is one exact known non-rollback process shape/state.
The combined closure passes `101/101` and contains no concrete network address.
The bounded attended-device review passed, fresh exact D0 and three-path
absence passed, and one exact V3403 approval was consumed. The transaction
aborted during rootfs staging before candidate intent: the USB-local payload
connection timed out because the host NCM link had no expected IPv4 address or
route. Candidate and rollback transfer counts are both zero. A later exact
health read repeated the blocked command-channel timeout, so the line is
stopped under the two-failure rule. The approval and run are non-reusable.
A separately approved D1 released the blocked receiver, removed only the empty
run-owned stage directory, and restored exact V2321 health. The stale
host-profile USB-path binding was repaired and direct NCM route/CIDR/ping now
pass. The first bounded review rejected a VID/PID-only NCM gate because another
Samsung target could satisfy it separately from the ACM bridge. The remediation
requires the sole NCM interface under the same USB parent as the manifest-bound
A90 ACM endpoint and passes the `105/105` focused closure. Independent
re-review returned `GO`. New run `a90-v3403-debian-f1-20260730-03` has a
new-inode exact rootfs/key pair, fresh V2321/path/NCM D0, a passing final
manifest inspection, and a host-only approval receipt. One exact approval was
then consumed. The 2 GiB rootfs staged through the topology-bound NCM path and
was rehashed immediately before intent. V3403 completed one checked boot
write/readback, booted with exact version/build, and passed selftest. The first
candidate-side remote source-preflight request was corrupted by console/menu
interference before the handoff phase, so the switch-root command was never
sent and Debian PID1 remains unproved. V3403 returned healthy and the exact
V2321 rollback completed one checked
write/readback. The initial final-health selftest lost its frame terminator
after rollback, but durable state already proved `rollback-flashed`; the
approved rollback-recovery path therefore performed read-only health checks
without reinvoking rollback and closed the transaction
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`. Candidate/rollback counts are `1/1`,
candidate replay is false, exact V2321 final health passed, and internal
userdata is untouched. The run and approval are non-reusable. The H0 successor
now binds explicit slow serial pacing, two framed hide/settle/canary gates, one
direct no-retry handoff, and first-byte deadline reservation. It rejects the
old 45-second handoff timeout and requires at least 905 seconds to preserve a
900-second full-path response window. Exact loader/runtime gates and mutation
checks bind that calculation. The focused closure passes `124/124`, and final
independent review returned `GO` with no device contact. A fresh connected-D0
attempt then proved exact A90 binding, healthy V2321, zero selftest failures,
zero pstore entries, and repaired the host-only topology-bound NCM profile.
Its serial SD-path read was rejected busy. A missing host fail-fast check then
passed an empty tcpctl token and triggered one unapproved automatic-menu
`hide`; the following tcpctl shell failed to parse before its body or any file
operation. Exact V2321 return health passed. The unit is stopped as
`STOP_UNAPPROVED_D1_HIDE_RETURN_HEALTH_PASS`: SD path state is unproved and no
new run, manifest, approval, staging, flash, or live authority exists. Resume
requires operator direction and a no-menu-control D0 path; no old approval or
run may be reused. The operator then directed resume. A no-menu-control
successor produced fresh connected D0 and exact three-path absence evidence.
The old fixed-name source remains untouched and excluded. The staging adapter
now derives one unique final source path from the exact run ID and byte-exactly
binds the manifest to it; legacy, cross-run, traversal, outside-root, and work
paths are rejected while hard-link no-clobber publication is unchanged. The
focused closure passes `125/125`, independent safety review returned `GO`, and
commit `b59c939d` contains the change. Fresh run
`a90-v3403-debian-f1-20260731-01` binds a new-inode keyed rootfs, observer key,
connected evidence, candidate, exact V2321 rollback, staging adapter, and
orchestrator. Both host inspections report zero issues. One private mode-0600
approval receipt is prepared with all authority false. No staging, flash, or
reboot has occurred; the next gate is one fresh exact operator acknowledgement
of that receipt's token. That exact approval was consumed. The unique rootfs
staged and rehashed successfully, and one candidate boot transfer completed.
V3403 returned its exact `0.11.159` build banner, but automatic menu output
interleaved after the version body and the required frame END was lost.
Candidate selftest, source preflight, handoff, `switch_root`, and Debian SSH
observation were never reached. One exact V2321 rollback then completed. Its
first final-health read met the same frame loss without repeating the transfer.
After one operator-approved low-risk menu hide, health-only recovery proved
exact V2321, selftest failure count zero, and zero pstore entries. The journal
closed `ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK`; durable candidate and
rollback start/completion records each occur once, candidate replay is false,
final health is restored, and internal userdata is untouched. The run and
approval are non-reusable. The selected successor is a future-only,
predeclared operator-attended observation window with bounded pre-handoff
channel/health retries, exactly one handoff attempt, and unchanged mandatory
rollback. Its reusable orchestrator implementation now binds exact `900/3/1`
limits into the manifest and original F1 approval, revalidates the exact
one-transfer/no-replay candidate closure, re-derives stored retry failures,
and fsyncs one handoff intent before dispatch. Focused `71/71` and independent
related `154/154` validation passed; final independent review returned `GO`
with no device contact. Fresh run
`a90-v3403-debian-f1-20260731-02` now binds a new-inode keyed rootfs and key,
fresh exact V2321 health and three-path absence, repaired topology-bound NCM,
and the reviewed `900/3/1` machinery. Both host inspectors and the strict local
closure report zero issues. A private mode-0600 approval receipt is prepared
with all authority false. One exact approval was consumed, but the staging
child rejected it before NCM, bridge, or device contact: its duplicated
approval-binding builder omitted the new attended `900/3/1` fields. The
durable transaction closed `ABORTED_F1_V2_BEFORE_CANDIDATE` with candidate and
rollback counts `0/0`, no rootfs staging, no reboot, and no continuation
receipt. The run and approval are non-reusable. The H0 repair now gives
staging and the orchestrator one canonical approval-binding builder with exact
run/hash and attended/unattended policy validation. Focused `111/111`, related
`157/157`, `py_compile`, and independent re-review passed with no Critical,
High, or Medium finding and no device contact. No new run, manifest, approval,
or live authority existed at repair closure. Fresh successor
`a90-v3403-debian-f1-20260731-03` now binds a new-inode rootfs/key, exact V2321
D0, three-path absence, topology-bound NCM, and the reviewed canonical
staging/orchestrator sources. Both host inspectors and strict local closure
report zero issues. The final manifest SHA256 is
`efc18c20a97d2c2a4418009d4202dc9dd85b7c61a83d563e70c3b0d225222206`.
A private mode-0600 receipt is reopened successfully by both approval
validators with exact `900/3/1` and all authority false. One exact F1 approval
and one attended continuation were then consumed. Rootfs staging, one candidate
boot transfer, candidate health, source preflight, and the first pre-handoff
attempt passed. The single handoff stopped in strict display cleanup before
storage or `switch_root`. A DRM owner remained alive at its one-second
per-owner deadline and produced `-EBUSY`; the immediately following
authoritative scan nevertheless proved zero remaining non-preserved owners.
The stale per-owner error stayed in `final_rc`, so the source was rehashed
unchanged and the handoff returned. Candidate native-init return passed. One
exact rollback transfer completed; its first final-health `hide` was corrupted
to `hidAe` by menu interleaving, after which health-only recovery performed no
transfer and proved exact V2321, selftest failure count zero, and zero pstore
entries. The transaction closed
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` with candidate/rollback `1/1`, no replay,
one handoff attempt, Debian PID1 unproved, and the canonical eight-event
timeline. The run and approvals are non-reusable; no A90 live authority
exists.**

Stock D1 v2 and the PM/source audits remain valid independent controls.
P2.86's retained `0xc18` still proves its strengthened exact parent-suspended
gate, and the source data-flow result that two early trace snapshots are only
classification enrichment remains true. Neither result explains the missing
successor checkpoint: the inherited active-slot state defect deterministically
returned `-ESTALE` before any restart marker could commit.

Follow-up contract H0 found that the retained slot already carries an unused
local-stage `item_index`. P2.88 is selected to use one finite, generated
`(stage,item_index)` position sequence after the unchanged generation-88
`0x8f` prefix. The 45-byte/two-slot layout, CRC protocol, and numeric
`0x8d..0x93` stages remain. Terminal generation rises only from 92 to 103, so
the exact accepted sequence length and generation upper bound are both 103.
Generation is a sequence index, not a free counter; the earlier “152 values
of headroom” framing was wrong. This
position channel marks helper dispatch, immediate helper return, later
readback/trace/cleanup, bind, and final-sampling boundaries without expanding
the record.

The historical stage-only model cannot accept that sequence:
`_stage_generation()` uses `sequence.index(stage)` and `apply_request()`
requires the next stage byte. P2.88 therefore needs a versioned pair-aware
model and must validate generation, stage, and item together. Runtime
publishers do not choose numeric wire coordinates: the checkpoint client
derives the exact next pair from generation, while generated symbolic labels
and a static success-path source-order gate prevent missing, repeated, or
reordered calls from being misattributed.

The current `validate_reachable_records()` is only an encodability/decoder
domain check; it does not inspect runtime or classifier source. P2.88 must add
a bidirectional active-producer route gate keyed by exact
`(stage,item_index,outcome,detail)`. The trace-dependent
`c57/c58/c59` details and the superseded `c5c` cleanup marker have zero active
P2.88 routes.

P2.88's 103-position pair model and P2.90's 107-position adjacent model remain
internally correct. Their validator, table, producer-route, and static-link
proofs established request encodability and publication topology, not writer
state resumability. The missing invariant is general:

```text
ACCEPT_TO_RESUME_CLOSURE:
accepted nonterminal states are a subset of resumable states
```

Every accepted committed slot must be represented byte-for-byte by kernel
expected state, and every declared successor must continue without active-slot
`-ESTALE`. The same closure applies to kernel writer, userspace client,
decoder, and model. This supersedes treating request acceptance, decode
success, linked table equality, or producer reachability as sufficient.

Both retained slots are valid, and generation 89 left no target-slot mutation.
Candidate-bound native replay now explains this exactly: active generation 88
was accepted and committed with `detail=0xc18`, but the writer retained no
detail in its expected state. The next write reconstructed `detail=0`, returned
pre-mutation `-ESTALE`, and left both retained slots unchanged. Changing only
the active detail to zero is a positive control and advances successfully to
generation 89.

The P2.88 and P2.90 linked-table and exhaustive-validator proofs remain valid
local evidence: they prove declared request encodability and exact linked
tables. They do not prove that every accepted committed state can be resumed.
Likewise, P2.90's adjacent coordinates, checked park routes, and request
construction were internally correct but could not overcome the inherited
active-state defect; primary and fallback publication both returned the same
`-ESTALE`.

P2.88's early trace-snapshot removals and P2.90's park accounting remain
historical implementation facts, not explanations for the live silence. The
deferred-close and child-observer proposals are withdrawn for this incident.
The bound decoder's generation-87 presentation correction remains valid and
does not change record validity or any closed F1 verdict.

No S22+ F1 live run is currently authorized. Both P2.84 stock-D1 approvals and
the P2.84, P2.86, P2.88, and P2.90 F1 approvals are consumed. Do not repeat
P2.82 or replay/rebuild P2.84, P2.86, P2.88, or P2.90.

P2.86 run `c6cde593033d6f1be93f82c8ff5a81e8` passed its frozen pre-intent
closure and pre-LTO qualification. Its first Full-LTO A/B pair failed closed:
`vmlinux` differed by exactly 138 eight-byte random private-path tokens in
`.debug_line` plus the derived 20-byte GNU build ID; `Image` differed only by
that build ID. The pair is invalid and no promotion occurred.

The selected correction changed no source byte or intent. A real copy of the
pinned clang repository was placed below the work tree's mapped parent and
only the private `--clang-repo` argument changed. Corrected A showed zero
random private-root and absolute clang-resource leaks before B started; the
corrected A/B pair then matched.

## Durable Established Evidence

- R4W1-D proves a 45-byte contiguous pre-cursor record, deterministic Full-LTO,
  live custom PID1 execution, exact rollback, and final health as
  `PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`.
- P2.37 and P2.39 prove terminal E1A and E1B respectively, including exact
  static-child execution/reap and the five-module visibility sequence.
- P2.58A passed terminal stage `0x8f` after exact UDC target membership at
  `0x87`; exact rollback and health passed.
- **P2.58A complete/closed, F1:** E2 through the real UDC is live proven;
  **E3-E4 next** remains the functional frontier.
- P2.71-P2.72 prove generic-arm64 configfs/ACM execution, clean Full-LTO A/B,
  linked audit, deterministic boot-only packaging, independent static closure,
  offline promotion, and immutable ready-manifest construction.
- P2.76 proves exact configfs UDC bind and synchronous pull-up request, but not
  configured state or host receipt. Exact rollback and health passed.
- P2.80 proves RUN_STOP plus `DEVCTRLHLT` clear while UDC remained
  `not attached`; exact rollback and health passed.
- P2.82 proved its NONE helper write returned, but a newline comparator made
  readback impossible. It is superseded and must not be repeated.
- P2.84 corrected that comparator, passed `20/20` pre-LTO, Full-LTO A/B,
  linked/package/static closure, one candidate transfer, one exact rollback,
  and final health. It is closed no-proof and immutable.
- P2.86's first Full-LTO pair failed closed with a completely attributed
  build-layout path leak. `1,124 = 138 * 8 + 20`; the 20-byte residual is
  exactly the GNU build ID, and Image has no other difference.
- P2.86's corrected Full-LTO A/B, linked/package/static closure, independent
  downstream-runner registration review, ready manifest, D0, one candidate
  transfer, exact rollback, and final health passed. Its formal live verdict is
  `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.
- P2.86 recovery resumed rollback-only after a USB inventory-membership race
  interrupted the first physical-Download endpoint snapshot. No candidate
  replay or rollback retry occurred.
- P2.86 retained `0xc18` proves its strengthened exact parent-suspended gate.
  The earlier attribution of the missing successor to tracefs, USB, PM, or a
  publisher non-return is refuted by the inherited writer-state defect.
- P2.88 implemented the 103-position pair-aware channel, removed both early
  classification-only snapshots, passed deterministic Full-LTO/package/static
  closure, and completed one candidate plus one exact rollback. Its retained
  state still ends at inherited generation 88; generation 89 and every new
  P2.88 coordinate remain unproved.
- P2.90 places adjacent `0x8f` coordinates, accounts for all historical parks,
  proves the `(0x90,0)` request construction, links byte-identical userspace,
  and exhaustively accepts exactly 107 of `7,077,888` validator inputs.
- P2.90 completed one candidate and one exact rollback with no replay and final
  health pass. Its formal verdict remains no-proof; generation 89 and every
  later E3 boundary remain unproved.
- A P2.84-through-P2.90 sweep finds exactly four affected F1 runs. All end in
  `generation=88/stage=0x8f/PROGRESS/item=0/detail=0xc18`, and all inherited the
  same writer/state spans. Native replay returns exact pre-mutation `-ESTALE`;
  the detail-zero positive control advances to generation 89.
- The same four runs establish a stable live prefix baseline: all 88 declared
  positions through generation 88 committed in four independent boots. Any
  repaired successor divergence before that tuple is a new regression signal.
- The successor load-bearing gate is `ACCEPT_TO_RESUME_CLOSURE`: every accepted
  nonterminal committed state must be byte-exactly representable and resumable
  by kernel writer, userspace client, model, and decoder.
- Exact source rejects treating a parent-PM sign or PHY flag as electrical
  proof; swallowed clock errors remain non-proof.
- Process v2 common D0/F1 execution, regular-path boot-only Odin transport,
  journal recovery, rollback, and final health are proven.
- A90 run `a90-debian-reactivation-f1-20260730-01` proves one exact V3402
  checked boot transfer, one exact V2321 checked rollback, and restored final
  health with no candidate replay. It also proves the current D3 handoff can
  mutate the bound SD rootfs before a later display-owner failure, so Debian
  PID1 remains unproved for this run.
- A90 V3403 closes the selected H0 successor: strict display cleanup occurs
  before storage, only a verified work copy can be mounted rw, every modeled
  pre-switch failure preserves the source, and a fresh authenticated D3
  sysvinit image is privately hash-bound.
- A90 V3403 run `a90-v3403-debian-f1-20260730-02` consumed one exact approval
  but aborted during SD staging before candidate intent. Candidate and rollback
  transfer counts are zero; the run is closed and non-reusable. The host NCM
  link lacked its expected USB-local IPv4 address/route, and the blocked
  receiver initially left command-channel health unverified. A separately
  approved D1 later restored exact V2321 health and removed only the empty
  run-owned stage directory. Host NCM now passes direct-route/CIDR/ping
  readiness; the topology-bound pre-reservation gate passes `105/105` and
  independent re-review.
- Fresh attended successor run `a90-v3403-debian-f1-20260731-02` passes exact
  V2321 health, three-path absence, topology-bound NCM readiness, both
  host-only inspectors, and strict local-closure validation. One exact approval
  was consumed, but staging rejected the receipt before any device contact
  because its approval-binding copy lacked `900/3/1`. Candidate/rollback are
  `0/0`; the run is closed and non-reusable. A shared canonical builder fixes
  the mismatch and passed independent re-review, but creates no new authority.
- Fresh successor `a90-v3403-debian-f1-20260731-03` passes exact V2321 D0,
  three-path absence, topology-bound NCM, both host inspectors, strict local
  closure, and cross-validator receipt reopening. Its approval and attended
  continuation are consumed. Staging and candidate health passed, but the one
  handoff retained a per-owner `-EBUSY` after its final owner rescan reached
  zero, so `switch_root` was not reached. Candidate/rollback are `1/1`, no
  replay, exact V2321 health is restored, and the run is closed.
- A90 V3404 run `a90-v3404-debian-f1-20260731-01` is closed healthy/no-proof
  with candidate/rollback `1/1`, no replay, and exact V2321 final health.
  Offline preservation of its 2 GiB work image proves Debian sysvinit PID1,
  firstboot, `/usr/sbin/init`, and Dropbear. Its live SSH contract failed after
  NCM profile loss, and the 120-second child entered global `sync`; reboot exec
  remains unproved. D0 excludes a missing reboot binary and proves sysrq
  enabled plus an active but kernel-petted hardware watchdog.
- A90 V3405 run `a90-v3405-debian-f1-20260731-01` is closed healthy/no-proof
  with candidate/rollback `1/1`, no replay, one handoff, and exact V2321 final
  health. All four immutable source hashes and `exec_switch_root_now` passed.
  Live USB-local SSH then proved `pid1_comm=init`, a distro init executable,
  `dropbear_started=1`, and the Debian marker in two attempts. The no-sync
  supervisor returned to the exact healthy candidate, as required before the
  from-native rollback, so the former global-sync return failure is bypassed.
  Formal observation remains no-proof because the first candidate-return
  channel check lost `A90P1 END`; retained-pmsg collection was therefore not
  reached. The first rollback health check also met menu corruption, after
  which health-only recovery performed no transfer and closed exact V2321.

Load-bearing current reports:

- `docs/reports/A90_DEBIAN_REACTIVATION_F1_CLOSED_2026-07-30.md`
- `docs/reports/A90_V3403_F1_STAGING_ABORTED_BEFORE_CANDIDATE_2026-07-30.md`
- `docs/reports/A90_V3403_ABSENT_ONLY_STAGING_ADAPTER_H0_2026-07-30.md`
- `docs/reports/A90_V3403_MINIMAL_F1_ORCHESTRATOR_H0_2026-07-30.md`
- `docs/reports/NATIVE_INIT_V3403_D3_IMMUTABLE_HANDOFF_H0_CLOSURE_2026-07-30.md`
- `docs/reports/NATIVE_INIT_V3404_D3_RESOLVED_OWNER_TIMEOUT_SOURCE_BUILD_2026-07-31.md`
- `docs/reports/A90_V3404_REUSABLE_F1_STAGING_BINDING_H0_2026-07-31.md`
- `docs/reports/A90_V3404_D3_SWITCHROOT_NO_PROOF_F1_CLOSED_2026-07-31.md`
- `docs/reports/A90_V3404_D3_WORK_COPY_POSTMORTEM_DEBIAN_PID1_PROVEN_2026-07-31.md`
- `docs/reports/A90_V3405_D3_SYNC_DECISION_SUPERVISOR_H0_2026-07-31.md`
- `docs/reports/A90_V3405_F1_RETAINED_PMSG_NCM_REBIND_H0_2026-07-31.md`
- `docs/reports/A90_V3405_DEBIAN_PID1_F1_CLOSED_2026-07-31.md`
- `docs/reports/S22PLUS_FYG8_P284_CONTROLLED_SUSPEND_F1_CLOSED_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_POST_SUSPEND_RESTART_GAP_FOCUSED_ANALYSIS_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_STOCK_OUTER_D1_V2_LIVE_NO_PROOF_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P284_STOCK_TRACE_PM_ORDER_CORRECTION_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P264_QUALIFICATION_LATENCY_POSTMORTEM_AND_IDENTITY_SPLIT_H0_2026-07-25.md`
- `docs/reports/S22PLUS_FYG8_P286_SUCCESSOR_CHANGE_CLOSURE_FREEZE_H0_2026-07-29.md`
- `docs/reports/S22PLUS_FYG8_P286_FULL_LTO_PRIVATE_PATH_REPRO_FAILURE_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_PARENT_TAIL_BOUNDED_RESTART_F1_CLOSED_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_POST_0X8F_SILENCE_ATTRIBUTION_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P286_EARLY_RESTART_TRACE_LOAD_BEARING_AUDIT_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_ITEM_INDEX_SUBPOSITION_SUCCESSOR_DESIGN_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_PAIR_ATTRIBUTABLE_IMPLEMENTATION_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_PAIR_ATTRIBUTABLE_RESTART_F1_CLOSED_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_GEN88_TO_GEN89_CORRIDOR_AND_RESET_REASON_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P288_NO_SILENT_PARK_AND_LINKED_VALIDATOR_H0_2026-07-30.md`
- `docs/reports/S22PLUS_FYG8_P290_POST_COMMIT_TAIL_AND_CHILD_OBSERVER_H0_2026-07-31.md`
- `docs/reports/S22PLUS_FYG8_P284_P290_ACCEPT_TO_RESUME_HISTORY_ERRATUM_H0_2026-07-31.md`
- `docs/operations/S22PLUS_FYG8_CANDIDATE_BUILD_QUALIFICATION_RUNBOOK.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`

The previous 899-line goal snapshot is preserved at
`docs/archive/roadmaps/GOAL_THROUGH_P284_PM_ORDER_2026-07-29.md`.
Archived text is evidence only; it grants no device authority.

## P2.86 Frozen Identity and Implemented Closure

P2.86 was selected and implemented through a host-only, pre-intent frozen
closure. Its intent, corrected Full-LTO pair, static/package closure, F1, exact
rollback, and final health are now complete historical evidence.

### Candidate identity closure

P2.86 inherits all 60 P2.84 SOURCE_KEYS byte-for-byte and adds exactly 10
versioned payload-determining SOURCE_KEYS, for 70 total. Existing P2.84 source
files are forbidden mutation targets.

The 10 additions are the contract spec, source contract, candidate intent, E3
runtime include, classifier include, trace contract, userspace build,
candidate builder, build orchestrator, and boot-only packager.

The candidate requirements are frozen:

1. wait for exact parent suspended on the existing stop deadline;
2. fix the final timeout class before kill/reap, use `WNOHANG` plus an
   auxiliary reap deadline, classify an unreaped child, and publish the exact
   terminal checkpoint before potentially blocking trace cleanup; on the
   normal restart path publish one cleanup-pending progress marker after final
   trace capture/classification and before kprobe unregister/RCU cleanup;
3. attach outer entry/return probes to actual `dwc3_otg_sm_work`;
4. distinguish helper dispatch and completion;
5. distinguish flush timeout, completed write, start-peripheral entry without
   return, and later readback failure;
6. preserve a bounded classified PERIPHERAL write for the residual outer tail;
7. bind every payload-determining implementation/build input in the source
   preimage and bind non-identity support in the approval bundle.

The machine-readable authority is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_p286_change_freeze.py`.
It prints all 70 planned SOURCE_KEY-to-path rows.

### Bundle-bound support closure

Twelve verifier/evidence files cannot change `boot.img` bytes and stay outside
SOURCE_KEYS: source-contract selector, change freeze, freeze report,
candidate-contract verifier, build-repro checker, candidate static checker,
E2 stock closure, linked audit, pre-LTO qualification, and decoder adapter.
The common typed-evidence validator and host-only Process v2 core are also
outside identity and are bundle-bound for the P2.86 registration path.
They remain fail-closed because the approval bundle binds them through
`bundle.sha256`.

The selector stays outside identity because registering a later P2.88 contract
must not rewrite P2.86's historical run ID. The preimage records the selected
contract ID explicitly; the contract/spec receipts remain payload-bound.

The freeze gate derives tracked changes from the union of
`git diff --name-only <base>..HEAD` and `git status --porcelain`, including
untracked files. That Git-derived set must equal the frozen declaration in
both directions; an omitted or overdeclared path fails. This is P2.64 Stage A.
The execution-identity split and independent-review Stage C remain a
post-P2.86 identity-design debt; this H0 does not implement them.

### Private D1 runner closure

D1 runner corrections are separate from candidate identity and limited to four
files under
`workspace/private/outputs/s22plus_fyg8_p284_stock_outer_d1_v3/`:

1. parse instance-trace spelling without an absent group prefix;
2. terminate/reap watchdogs immediately on disarm;
3. remove the newline from the `/proc/self/comm` write;
4. remove the unapproved endpoint-count predicate.

The gate rejects equality and ancestor/descendant overlap between any D1 path
and candidate direct source path. It currently reports zero overlap. This
private repair list grants no D1 authority and is not a reason to rebuild.

### Intent stop gate (satisfied before derivation)

Intent derivation was prohibited until:

- all 10 payload sources and all twelve bundle-bound support files exist;
- the freeze tool reports `pre_intent_ready: true`;
- the successor contract reports exactly 70 SOURCE_KEYS;
- P2.84 receipts still match its frozen intent `60/60`;
- the Git-derived and declared tracked change sets are exactly equal;
- semantic and fault-injection tests cover all seven candidate requirements;
- D1 paths remain private with zero overlap; and
- `git status --short` is clean.

After intent, all 70 selected source receipts are immutable. A later payload
source change invalidates the A/B pair and requires a fresh intent. A
non-identity support change does not alter boot identity, but its validators
must be rerun and its final bytes rebound by `bundle.sha256` before approval.

### P2.86 implementation validation

The frozen 18-file overlay implementation is complete. No P2.84 source was
modified. The P2.86 intent and pre-LTO qualification are complete; the first
Full-LTO pair was retained as invalid diagnostic evidence after its exact
private-path attribution. At that failed-pair boundary no candidate was
promoted and no device was contacted. A later source-identical corrected pair
passed and supported the closed F1 recorded above.

The runtime now:

- waits for exact parent `runtime_status=suspended` on the existing stop
  deadline after the inherited child-suspended boundary;
- fixes timeout state before kill/reap, eliminates the blocking specific-child
  `wait4`, and uses `WNOHANG` under a 1000 ms auxiliary reap deadline with an
  exact unreaped-child class;
- publishes each exact terminal failure once before best-effort trace cleanup,
  so kretprobe unregister/RCU/tracefs cleanup cannot suppress or replace the
  original stage/detail;
- splits normal cycle finalization into capture/classification and cleanup,
  then publishes one `restart-trace-cleanup-pending` progress detail before
  kprobe unregister/RCU cleanup; at that boundary the two retained slots are
  the prior `0x8f` result and this `0x90` marker;
- records actual `dwc3_otg_sm_work` entry/return separately from the renamed
  `dwc3_otg_start_peripheral` entry/return pair;
- snapshots residual outer work before PERIPHERAL dispatch so a pre-existing
  tail, a flush timeout, and a newly entered start-peripheral no-return remain
  distinct; and
- separates helper dispatch, completion, write error, completed write plus
  failed readback, and the inherited later restart postconditions.

The source contract resolves exactly `60 + 10 = 70` keys. The selector and all
other pure verifier/evidence support remain outside identity. Generated
checkpoint and kernel validators accept the thirteen new exact details
`0xc50..0xc5c`; the linked adapter uses a 59-entry four-byte detail table. The
freeze gate also reopens run `023060c8dd0ab036f8547a816624356f` and verifies
all inherited P2.84 source receipts `60/60` with zero changed keys.

Static and fault validation passes the P2.86 focused suite, its full inherited
pre-LTO focused inventory, source/packager mutation rejection, deterministic
one-member `boot.img.lz4` packaging, AArch64 static classifier execution under
QEMU, deterministic userspace two-link/source implementation audit, clean
kernel-patch application, and the Git-derived freeze gate. An AArch64 harness
extracts the production abort function and proves `publish -> cleanup entry`
before remaining blocked forever in injected trace cleanup. The later live gap
does not invalidate those local assertions; it exposes untested blocking
operations before the asserted publication boundaries.

## Ordered Execution

1. Preserve the closed P2.90 journal, structured result, transfer receipts,
   byte-identical retained reads, USBFS diagnostic, and final health.
2. Keep P2.84, P2.86, P2.88, and P2.90 closed and immutable. Do not replay or
   rebuild them.
3. Preserve the four-run historical sweep and corrected cause: committed
   nonzero-detail progress state was accepted but not resumable, so the next
   write returned pre-mutation `-ESTALE` and userspace intentionally parked.
4. Implement P2.64 Stage C: one descriptor produces disjoint Tier 1 payload,
   Tier 2 qualification/provenance, and Tier 3 package/live receipt sets;
   require its mutation matrix and independent review before closing the debt.
5. Pass `CHECKPOINT_SOT_ZERO_DELTA`: freeze retained intent-bound P2.90 artifact
   SHA256s as the baseline, require clean run A to match it, then require clean
   run B to match both that baseline and A; repairs remain forbidden.
6. Prove `ACCEPT_TO_RESUME_CLOSURE` exhaustively across kernel writer,
   userspace client, model, and decoder. Then prove
   `ACCEPT_TO_RESUME_SEQUENCE_WALK` by continuously walking the exact
   runtime-derived 107-position stream from seed through terminal without
   resetting state, including a producer-derived runtime-reachable walk with
   consecutive nonzero-detail progress records.
7. Separately prove `CHECKPOINT_ERRNO_OBSERVABILITY`: preserve exact returned
   errno and produce bounded causal evidence before every park.
8. Recompute SOURCE_KEYS before intent. Keep SoT/generator and every
   byte-affecting output inside identity; keep verifier, decoder adapter,
   selector, freeze report, and prose outside and approval-bundle-bound.
9. Prove the inherited 87-position detail-zero prefix remains byte-identical,
   preserve valid nonzero progress detail, and retain fail-closed corruption
   handling. Do not add deferred-close or child-observer machinery.
10. Treat the four-run generation-88 tuple as the live prefix baseline; any
   earlier divergence is a regression. If a closure-proven successor is silent
   again, stop code-position tracing and test coupling to the system-state transition.
11. No new S22+ device action or F1 request is permitted by the closed P2.90
   unit; a successor requires fresh H0 design, identity, A/B, manifest, D0, and exact approval.

The A90 branch proceeds independently:

1. Preserve the closed A90 journal, structured result, raw private evidence,
   and exact V2321 final-health state.
2. Do not replay V3402 or reuse the consumed approval.
3. Preserve V3403's completed H0 source contract: display-owner cleanup before
   storage, source recheck, absent-only work copy, and failure cleanup.
4. Preserve the fresh D3 rootfs identity and its authenticated package,
   clean-ext4, ownership, init, and credential-absence closure.
5. Preserve the independently reviewed attended-orchestrator closure and its
   exact `900/3/1`, candidate-one/no-replay, durable-intent, and rollback-only
   recovery gates.
6. Preserve closed run `a90-v3403-debian-f1-20260731-02`, its consumed
   approval, `0/0` transfer counts, and before-device failure evidence.
7. Preserve closed run `a90-v3403-debian-f1-20260731-03`, its consumed
   approval and continuation, `1/1` transfers, one handoff, source-unchanged
   failure, final V2321 health, and no-proof verdict.
8. Preserve closed V3404 run `a90-v3404-debian-f1-20260731-01`, its consumed
   approval and continuation, one handoff, candidate/rollback `1/1`, exact
   V2321 health, no replay, and no-proof verdict.
9. Preserve the 2026-07-03 switch-root proof and V3404's exact D0 work-image
   preservation. V3404 now technically proves Debian sysvinit PID1 and
   firstboot; do not classify it as an image-payload or SELinux-init failure.
10. Preserve the independently reviewed V3405 no-sync parent supervisor and
    exact private H0 image; its artifact-build GO is not live authority.
11. Preserve closed V3405 run `a90-v3405-debian-f1-20260731-01`, both consumed
    approvals, candidate/rollback `1/1`, one handoff, live SSH Debian PID1,
    automatic healthy candidate return, and exact V2321 final health. Preserve
    its formal no-proof distinction: the first return-channel frame failed
    before retained-pmsg collection. No approval is reusable and no A90 live
    authority remains.

No device step is added when H0 can answer the question.

## Process

For each bounded unit:

`STATE -> SELECT -> DESIGN -> IMPLEMENT -> STATIC VALIDATE -> DEVICE -> REPORT -> COMMIT`

Use scoped staging. Never alter a selected source after intent. A reporting
failure after a proven device transition must not repeat that transition.

## Success Conditions

The post-PID1 frontier closes only through separate Process v2 rungs proving:

- mounts/readbacks plus one exact static child token, exit, and reap;
- watchdog and USB module results separately from platform bind and UDC;
- exact device-to-host ACM bytes; then
- one bounded host request and nonce-bound response.

Every live rung requires exact boot-only identity, bounded evidence, exact
rollback, final Android/root/supporting-partition health, and a complete
journal. No later rung may infer an earlier unproved result.

## Stop Conditions

- A permanent boundary in `AGENTS.md` would need to change.
- A P2.84 frozen source would need modification.
- A P2.86 payload source changes or is added after intent.
- Corrected A retains a random private-root or absolute clang-resource path.
- Candidate and D1 path closures overlap.
- Recovery, rollback, target identity, or Odin endpoint is unavailable.
- An unexplained device-session failure or repeated material failure occurs.
- Three consecutive units add only policy or review with no tested behavior.
- The S22+ branch grows to shell, NCM, Debian, or a supervisor before E4
  closes. A90 remains a separately authorized target and evidence line.
