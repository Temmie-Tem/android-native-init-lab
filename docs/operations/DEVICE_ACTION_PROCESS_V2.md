# Device Action Process v2

Status: P2.1-P2.5 complete; P2.6-P2.10 host path complete; R4W1-D exact
candidate proof and rollback passed; R4W1-E E1 closed with rollback but no
retained proof. No S22+ F1 run is currently authorized.

This process replaces per-candidate live helpers, policy activation commits,
per-run one-shot clauses, and repeated review ladders for ordinary boot-only
experiments. It does not relax the permanent boundaries in `AGENTS.md`.

## Design Goals

- Keep irreversible authority small and explicit.
- Make recovery part of the original authorization.
- Separate host failures from device-session and transfer failures.
- Resume evidence collection without repeating a completed device transition.
- Change candidate data through manifests, not source forks.
- Produce enough structured evidence for routine runs without mandatory prose.

## Components

### Target Profile

One versioned profile per target records stable facts:

- public model, device, and firmware identity;
- Android and Download identity rules;
- allowed boot-only transport and Odin version;
- healthy baseline and final-health predicates;
- rollback artifact reference;
- physical recovery instructions; and
- private evidence references without embedding device serials.

Changing target identity, transport, or recovery semantics changes the profile
and requires one independent review.

### Candidate Manifest

A manifest is data, not executable policy. It contains at least:

```json
{
  "schema": "device_action_f1_candidate_v2",
  "run_id": "...",
  "target_profile": "...",
  "candidate_ap": {"path": "...", "size": 0, "sha256": "..."},
  "rollback_ap": {"path": "...", "size": 0, "sha256": "..."},
  "allowed_member": "boot.img.lz4",
  "observation": {"timeout_sec": 0, "acceptance": "..."},
  "final_health_profile": "...",
  "runner_version": "..."
}
```

Paths must resolve to ordinary regular files at stable absolute names. Both APs
must contain exactly one regular `boot.img.lz4` member. A manifest cannot add a
partition, slot, primitive, or exception.

### Generic Runner

The H0 core is
`workspace/public/src/scripts/revalidation/device_action_f1_v2.py`. It currently
owns validation, plan rendering, and host-only simulations. The reusable D0
adapter is
`workspace/public/src/scripts/revalidation/device_action_d0_v2.py`. It reuses
the H0 bundle validator and exposes only validation, plan rendering, and one
connected read-only mode. Neither component exposes a live F1 transfer mode.
The reusable F1 adapter is
`workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py`. It
reuses these cores and exposes separated `--prepare`, `--execute`, and
`--recover` phases rather than a candidate-specific runner.

The F1 adapter owns:

- H0 artifact and manifest validation;
- D0 target preflight;
- approval binding;
- Android-to-Download target continuity;
- regular-path Odin invocation;
- append-only journaling;
- bounded observation;
- mandatory rollback; and
- final health verification.

Candidate markers, hashes, timeouts, and acceptance predicates are manifest or
profile data. They are not reasons to fork the runner.

### D0 Qualification

The reusable D0 adapter has no reboot, Download transition, Odin invocation,
partition transfer, F1 authorization, or live authorization path. Its connected
mode performs only bounded reads:

- exact one-target ADB enumeration and topology continuity;
- public target/profile properties and boot-health predicates;
- root identity and hashes of boot plus supporting partitions;
- one EOF-bounded manifest observer capture into a private run directory; and
- initial and final host USB inventories proving no Download endpoint.

Serial, topology, and boot identifiers are retained only as SHA256 digests in
the structured result. The strict result validator reopens the private raw
observer and proves its stable regular-file identity, size, hash, marker
cardinality, target evidence, health, USB state, and all no-authority flags.

On 2026-07-21 one connected FYG8 D0 run returned
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`. It read 2,097,136 observer
bytes to EOF with empty stderr, zero marker-family matches, and zero Download
endpoints before and after. The independently reviewed implementation and live
evidence are recorded in
`docs/reports/DEVICE_ACTION_PROCESS_V2_D0_QUALIFICATION_PASS_2026-07-21.md`.
This PASS qualifies the reusable preflight only and creates no F1 authority.

### F1 Adapter Source Gate

The reusable adapter passed focused simulations and two independent Claude
Opus read-only reviews on 2026-07-21. The final verdict was
`GO_HOST_SOURCE_TO_SEPARATE_MANIFEST_READINESS_AND_D0_PREPARE`. It closes the
source gate only.

The adapter binds the H0 bundle, D0 result, private target continuity, exact
execution-critical source closure, candidate and rollback artifacts, and
observation rule into one approval token. It reopens that evidence before
execution, repeats D0, tracks the measured Samsung Download endpoint, invokes
regular-path Odin, and resumes only mandatory rollback after a durable
candidate-attempt event. Candidate and rollback evidence are append-only;
state-bound pre-Odin checkpoints enforce the two-attempt limit, and a durable
completed rollback result is resumed without retransmission. Final PASS
requires exact candidate completion, exact retained-marker classification,
verified Magisk rollback, final health, and the canonical eight events.

The default manifest remains `draft-host-only` and `--prepare` refuses it before
run allocation. A separately named data-only canary manifest now has
`ready-for-f1-approval` status. One connected D0 preparation passed and produced
a private exact target binding without reboot, Odin, transfer, or device write.
`--execute` reopens only that prepared binding. No operator approval or F1 run
occurred in the source, readiness, or preparation units. See
`docs/reports/DEVICE_ACTION_PROCESS_V2_F1_ADAPTER_HOST_PASS_2026-07-21.md`.

The first later approved invocation stopped before candidate attempt or Odin
transfer when a Download node arrived between an empty snapshot receipt and its
post-receipt revalidation. The minimal fix permits only endpoint-arrival polling
to continue after that empty receipt; tickets and terminal absence remain
strict. Tests and independent review passed. The aborted binding is not reusable.
See `docs/reports/DEVICE_ACTION_PROCESS_V2_F1_CANARY_PRESESSION_USBFS_ARRIVAL_INCIDENT_2026-07-21.md`.

The next candidate, R4W1-D, was constructed without another runner or policy
fork. Thin data-contract adapters reuse the existing fixed-interval builder and
independent checker. Three distinct reproductions are byte-identical, the
independent static contract passes, and the Process v2 offline D0 gate accepts
the exact boot-only AP and rollback bundle. A later connected D0 passed, a
data-only ready manifest changed only IDs and readiness state, and F1
preparation repeated the read-only D0 and created an exact binding. No reboot,
Download transition, Odin invocation, transfer, or F1 authorization occurred.
See
`docs/reports/S22PLUS_FYG8_R4W1D_PROCESS_V2_CANDIDATE_HOST_CLOSE_2026-07-21.md`.
The connected/prepared close is recorded in
`docs/reports/S22PLUS_FYG8_R4W1D_CONNECTED_D0_PREPARED_PASS_2026-07-21.md`.

The exact R4W1-D prepared binding was approved once. Candidate and Magisk
rollback transfers each completed exactly once, two final retained-log reads
were byte-identical and contained one exact D proof, and final Android/Magisk
health passed. The journal closed with the canonical eight events and verdict
`PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`. See
`docs/reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`.

Both successful Odin transfers were followed by a false endpoint-identity
observation exception while the completed transfer reboot removed the USBFS
node. Durable transfer receipts allowed `--recover` to resume without
retransmission and complete the run. The host maintenance fix is now closed:
only the candidate and rollback post-transfer checks opt in, and only a
complete inventory transition equal to `baseline - exact Odin node` is emitted
as a persisted live-empty receipt. Strict post-receipt revalidation rejects a
replacement before acceptance. Incomplete inventory, arrivals, replacements,
and all default callers remain fail-closed. No repeat device run was needed.

### Typed Retained Evidence

P2.10 extends only the observation contract. The legacy exact-marker kind is
still accepted with its original bounded-string schema and classification. The
new `retained_checkpoint_after_rollback` kind is restricted to the reviewed
R4W1-E E1 decoder and pins both the P2.9 run manifest and independent static
checker result as regular files with exact sizes and SHA256 values.

Bundle validation recomputes the canonical run-manifest identity, binds its
16-byte run ID to the exact boot-only candidate AP, and includes the typed
evidence helper plus checkpoint decoder in the execution-critical closure. D0
continues to require the complete marker family to be absent before approval.
After rollback, acceptance requires one exact retained entry, no duplicate or
partial family, the expected run ID, terminal E1 success, and two CRC-valid A/B
slots with adjacent generations and a self-consistent saturated boot identity.
Progress, explicit failure, one-slot fallback, corrupt committed slots, stale
run IDs, and truncated regions are diagnostic only and cannot produce PASS.

The exact draft and ready manifests differ only in IDs and readiness state.
The focused 62-test execution-closure suite and independent H0 review pass.
This is a host-only capability change: it did not contact a device, perform D0,
invoke Odin, authorize F1, or flash. A connected D0 preparation and fresh exact
approval remain separate requirements.

The later approved R4W1-E E1 invocation transferred the exact candidate and
exact Magisk rollback once each. Odin returned success for both, the canonical
eight events are complete, final Android/root/supporting-partition health
passed, and the journal closed. Two complete post-rollback observer reads were
byte-identical but contained neither the E1 entry family nor `S22C` slot magic.
The strict verdict is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, not an E1 failure
or success claim. The consumed binding is not reusable. Host analysis must
separate runtime target/header gate refusal from loss of the larger retained
region before another candidate is designed. See
`docs/reports/S22PLUS_FYG8_R4W1E_E1_F1_LIVE_NO_PROOF_ROLLBACK_PASS_2026-07-22.md`.

P2.24-P2.25 later isolated and fixed the P2.23 current-node `reg` parser defect
and linked a bounded cache-flush PoC. P2.26 independently closed one new
boot-only candidate, P2.27 promoted its typed evidence, and P2.28 passed the
reusable live adapter's connected read-only preparation. That prepared binding
was consumed by P2.29. Candidate and rollback transfers completed once each,
final health passed, and two exact USERSPACE records were retained after a
separately clean baseline. The operator confirmed two candidate boots after a
missed physical Download entry. The immutable exact-one decoder therefore
preserves the formal `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` verdict even though
the records establish one userspace callback per observed candidate boot.

P2.30 does not alter that decoder or verdict. It adds a separate acceptance
kind and fixed policy identity for future manifests. With a separately clean
baseline, only one or more pure exact USERSPACE records are accepted. ENTRY,
UNSAT, zero, mixed state classes, either foreign family, and either snapshot
edge partial are non-positive or integrity failures. The execution-critical
closure binds both the P2.30 policy decoder and the unchanged P2.19 record
decoder. Archived P2.29 raw bytes replay positive only under P2.30; this is H0
analysis, not a retroactive F1 PASS. No ready manifest or live authority exists.

P2.31 correlates that accepted H0 replay with the exact P2.26 AP, completed
P2.29 transfer, request ABI, userspace control flow, and kernel gate. This
technically establishes PID1 procfs mount, `statfs(PROC_SUPER_MAGIC)`, and the
kernel store of the first E1 request. It does not change P2.29's formal verdict,
prove the write returned, or authorize a later E1 or E2 rung.

### Append-Only Journal

The runner creates one exclusive run directory and appends immutable transition
records. Each record contains a sequence number, UTC timestamp, state, action,
artifact identities, target evidence digest, outcome class, and references to
private raw logs. A separately fsynced high-water head records the latest
sequence and record hash. A missing or shorter tail fails closed; a valid record
written just before a crash may advance a lagging head during reopen.

The journal is designed for accidental loss, interrupted writes, and ordinary
operator mistakes on an operator-controlled host. Its SHA256 chain is not a
keyed MAC and does not claim to resist a malicious host owner who can rewrite
the chain and head together.

At minimum, distinguish:

- `host_preflight_failure`
- `odin_local_parse_failure`
- `download_endpoint_not_found`
- `odin_device_session_started`
- `candidate_transfer_started`
- `candidate_transfer_completed`
- `observation_completed`
- `rollback_transfer_started`
- `rollback_transfer_completed`
- `final_health_verified`
- `aborted`

Never infer a partition write from process launch alone. Never erase or replace
an earlier journal entry. A result generator reads the journal; it does not
control whether a completed transition is repeated.

## State Machine

```text
PREFLIGHT
  -> APPROVED
  -> DOWNLOAD_IDENTIFIED
  -> CANDIDATE_FLASHED
  -> OBSERVED
  -> RECOVERY_DOWNLOAD
  -> ROLLBACK_FLASHED
  -> HEALTH_VERIFIED
  -> CLOSED
```

Any state may move to `ABORTED` when its stop condition fires. A restart reopens
the journal and resumes only an allowed next transition. It never repeats a
transition that has durable completion evidence.

## Approval

One fresh approval is collected after preflight and immediately before the
first write-capable transition. It binds:

- exact target profile and live target evidence digest;
- candidate and rollback AP SHA256;
- manifest SHA256;
- runner and Odin versions;
- observation timeout and acceptance rule; and
- the mandatory recovery plan.

That approval authorizes one candidate attempt and all necessary execution of
the exact rollback plan. No second acknowledgement may block rollback after the
candidate attempt begins. A changed binding requires a new preflight and new
approval.

Preflight, dry-run, and local Odin parser failures are durable run outcomes but
not permanent one-shot consumption. A later attempt is a new run and requires a
new approval. The process does not reactivate or reuse an old approval.

## Regular-Path Transport

- Open candidate, rollback, and Odin files before Download transition.
- Verify regular-file type, size, SHA256, and AP membership from those files.
- Pass Odin the real absolute `.tar.md5` pathname.
- Forbid `/proc/self/fd`, memfd, extensionless aliases, and path rebinding.
- Record whether Odin reached local parsing, endpoint setup, device session,
  transfer start, and transfer completion. Only a recognized local parse error
  may be classified pre-session; every ambiguous failure is treated as a
  possible device-session failure.
- Recheck file descriptor identity and content after subprocess return.

## Recovery

Rollback is a normal state-machine transition, not a new experiment. Before the
candidate flash, prove the rollback AP is readable, hash-correct, single-member,
and usable through the demonstrated Download path.

If candidate Android or ADB does not appear, the bounded observation timeout
ends and the operator physically enters Download. The runner then performs the
exact approved rollback. It does not repair the candidate, change transport, or
try another candidate.

If rollback fails after an Odin device session begins, stop experimentation and
escalate recovery. Only a separately invoked `recover` action may consume the
remaining attempt within the durable two-attempt bound, using the same exact
preapproved rollback; the failed invocation does not retransmit automatically.
Do not launch a second candidate. A stock boot cleanup path, when a target
profile supports one, is recovery-only and cannot produce PASS.

## Evidence

Routine F1 evidence consists of:

- the candidate manifest and its SHA256;
- the append-only journal;
- private raw Odin and observer logs;
- one structured result with failure taxonomy; and
- the canonical eight-event public timeline.

Write a prose report only for a new capability, hazard, incident, ambiguous
result, recovery deviation, or policy change. A normal repeated PASS needs no
candidate-specific policy document.

## Review Boundary

Review the execution-critical closure only:

- runner;
- manifest/profile validators;
- AP member verifier;
- Odin wrapper/version;
- journal/resume logic;
- observation parser; and
- final health verifier.

One independent review is enough when this closure or a hazard class changes.
Candidate data changes require fresh validation and approval, not a repeated
architecture review. Unreachable retired helpers and historical reports are not
runtime dependencies and must not enter the SHA gate.

## Migration Gate

No F1 live run is authorized until all of these pass host-only:

1. target profile and manifest schema validation;
2. generic runner state-machine tests;
3. AP extra-member and forbidden-member rejection;
4. wrong-target and target-ambiguity rejection;
5. changed/missing rollback rejection;
6. local Odin parse-failure classification;
7. simulated interrupted-result resume without transition replay;
8. simulated candidate timeout to rollback;
9. structured result and canonical timeline validation; and
10. one independent review of the execution-critical closure.

All ten host migration gates passed on 2026-07-21, including the independent
review and remediation re-review. The verdict was
`GO_HOST_CORE_TO_D0_IMPLEMENTATION`; it authorizes neither device contact nor
F1. The existing R4W1-C3 implementation remains inactive reference evidence
for regular-path transport and must not become an interim live exception.

P2.4 then passed focused tests, independent D0 review, and one bounded connected
read-only qualification. The P2.5 reusable adapter source and execution closure
now pass host-only. No F1 run is authorized: the manifest remains draft, no D0
preparation binding exists for this canary, and no fresh exact approval has been
given.
