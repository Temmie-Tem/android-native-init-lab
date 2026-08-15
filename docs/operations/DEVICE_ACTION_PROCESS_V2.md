# Device Action Process v2

Status: P2.1-P2.5 complete; P2.6-P2.10 host path complete; R4W1-D exact
candidate proof and rollback passed; R4W1-E E1 closed with rollback but no
retained proof. No S22+ F1 run is currently authorized.

The A90-only resident boot-promotion v1 policy is adopted as a target-specific
extension. Its independently reviewed H0 runner has no final connected
manifest, approval, or device authority. It does not alter the ordinary state
machine below or any S22+ run.

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
After a complete bounded baseline capture, a retained-family or decoder
rejection must publish one typed, no-replace `result.json` before returning the
stop. That stop receipt binds the raw bytes, initial target/health/USB evidence,
and all zero-effect flags, explicitly records that final continuity and final
health were not observed, is non-reusable, and can never satisfy D0 success or
prepared-run validation. A failure before a complete bounded capture makes no
such raw-evidence claim.
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

This remains the ordinary F1 state machine. The A90-only F1-RP state machine
and its distinct `PROMOTED_CLOSED` terminal are defined in
`A90_RESIDENT_BOOT_PROMOTION_V1.md`. F1-RP does not add an ordinary Process v2
terminal and cannot be selected by an ordinary candidate manifest.

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

### Result-Contract Arming Precondition

An F1 approval may not bind an observation timeout and acceptance rule whose
result contract has been demonstrated only on its success path. Before that
approval is collected, the qualification must show that every terminal state of
the result contract, including each failure bucket, decodes to its intended
classification from a synthesized retained representation. The demonstration is
host-only and must exercise the real encoder, the real carrier representation,
and the real host decoder rather than a stand-in for any of them.

The gate binds the encode and decode path, not the device condition behind it.
A terminal state qualifies when a synthesized carrier representation decodes to
exactly that state; reproducing the physical condition that would emit it is
neither required nor sufficient. A state whose representation cannot be
synthesized and decoded at all is unreachable in the decoder and is therefore
not admissible in the result contract. Once an approval exists, removing an
admitted state is a contract change that requires a new preflight and new
approval.

A capability proof does not satisfy this precondition. The mechanism under test
and the observer that must report it are separate objects; this gate binds the
observer.

The precondition exists because a run whose observer cannot express its own
failure consumes the candidate, the attendance, and the rollback budget while
returning no information about the device. The campaign ledger records that
outcome as `NO_PROOF_OBSERVER`. It is a durable run outcome, not a retry, and
the consumed candidate is never replayed.

An observer-valid terminal that proves a necessary in-candidate experiment
precondition was false is different. It is recorded as
`NO_PROOF_EXPERIMENT_PRECONDITION`: the observer is sound, the mechanism under
test did not execute, and neither `PROVED` nor `REFUTED` is permitted. Host
channel degradation may coexist with that result, but does not replace a
CRC-clean, authority-complete retained precondition terminal. The original
terminal spelling and append-only action row remain evidence; a later
classification correction may change only the effective campaign metric and
must identify the original row and its source-backed reason.

### Experiment Executability Closure

The result-contract arming precondition proves that the observer can report
every admitted outcome. It does not prove that the candidate can reach the
mechanism under test. An ordinary Process-v2 candidate must therefore carry a
second, independent `EXPERIMENT_EXECUTABILITY_CLOSURE` before approval.

This is an explicitly permanent common qualification boundary, not a temporary
P3.17 gate. It blocks the
`UNMODELED_EXPERIMENT_DEPENDENCY_PRECONDITION` hazard exposed by P3.16 and
applies to ordinary Process-v2 causal experiments. It has no expiry. Retiring
or weakening it requires a reviewed common-contract change proving that every
supported candidate obtains equivalent execution-precondition closure
elsewhere. A false admission or false block, a newly discovered non-symbol
dependency family, or a change to a registered extractor's kernel, firmware,
boot-argument, or package authority triggers review. Every new relation family
requires proportional independent review before use.

The closure starts from the experiment design's explicit **must-bind consumer
set**, but registered relationship families are not root-only passes. Let
`S[0]` be the reviewed must-bind set. Qualification computes the least fixed
point

`S[n+1] = S[n] union fw_devlink_suppliers(S[n]) union device_instantiators(S[n]) union driver_consumed_dt_dependencies(S[n])`

over exact source-derived device or firmware-node identities. Equivalently,
the right-hand side is the union of every registered relationship family, so a
new family cannot be registered without entering the same iteration. Every
node emitted by any family re-enters **all** registered families on the next
iteration. Therefore a supplier's own creator, an instantiator's own fw_devlink
suppliers, and a driver-consumed reference's own predecessors are all in
scope. Stop only when no new exact node or required edge is produced.
Termination follows from the finite exact candidate firmware/device-node
universe; a repeated identity is deduplicated, not re-expanded. Root-only or
single-family analysis is forbidden.

For each node in this working set, qualification must enumerate every
dependency graph that can prevent the claimed execution but is not represented
by the selected module symbol graph. A graph family may be declared empty only
by an executed, source-bound extractor. An unclassified relation, unresolved
required edge, unknown creator, or missing provider blocks packaging; it is not
deferred to attended F1. Existing membership in a historical module plan is an
output to verify, never a seed assumption that closes the relation.

The first registered family is `FW_DEVLINK_DT_SUPPLIER_CLOSURE`. Its authority
is the exact fixed kernel's `of_supplier_bindings[]` parser table, exact device
tree, effective `fw_devlink` mode and strict value from all boot-argument
sources, and the candidate module/built-in plan. A raw scan of every phandle is
not equivalent to the kernel parser and is forbidden as closure evidence.
This family applies only to must-bind consumers whose exact kernel path uses an
OF fwnode and the registered parser authority; it is not permission to expand
the module plan from every node in the device tree.

The second registered family is `DEVICE_INSTANTIATION_CLOSURE`. It covers a
different graph: a required device may not exist until another device's probe
populates it, or until a bus/adapter registration enumerates its firmware
children. Such an instantiator is an explicit must-bind root when starting the
supplier closure from the not-yet-created consumer would make the dependency
structurally invisible. Its authority is the exact parent/bus driver source,
the exact firmware-node parent/child and match relationship, the exact
population or enumeration call path, and the candidate built-in/module and
load-order plan. The first registered mechanisms are default OF platform
population, SPMI controller child enumeration, parent-driver OF child
population, and OF I2C-child creation through adapter registration and
`of_i2c_register_devices()`.

For every node in the fixed-point working set, qualification must classify how
that device comes to exist. A statically created device, a parent-populated
platform child, a bus-enumerated firmware child, and an unclassified creator
are distinct states. An unclassified creator, absent required instantiator, or
order that allows the dependent probe before its instantiator blocks
packaging. This family does not turn every bus parent into a reviewed causal
root: only the original claim-to-consumer set is a root judgment, while
source-derived instantiators are closure predecessors with recorded
provenance.

The third registered family is `DRIVER_CONSUMED_DT_REFERENCE_CLOSURE`. It
covers exact DT relationships that a driver parses and enforces directly but
which the fixed `of_supplier_bindings[]` table does not convert into a
fw_devlink edge. Its authority is the exact consumer driver function boundary,
the exact property parser and referenced-node lookup, the failure or defer
condition when the referenced device or bound-driver state is absent, the
exact DT property and target identity, and the module/built-in and order plan.
For P3.17 the first registered relation is the GENI I2C driver's
`qcom,wrapper-core` reference: `994000.i2c` and the QUPv3 wrapper are siblings
created by default OF platform population, while the I2C probe requires bound
wrapper driver data and returns `-EPROBE_DEFER` before adapter registration
when it is absent. A direct driver-consumed reference is neither a fw_devlink
supplier edge nor proof that the referenced driver instantiated the consumer.

Each causal claim must also name its **evaluability preconditions**, including
non-root runtime/observer facts such as an already-active gadget path or a
host-sidecar arm receipt. Qualification mechanically enforces presence and
coverage of those declarations; it does not certify their causal truth merely
because text exists. The candidate-specific closure must prove each declared
precondition with its stated runtime or retained authority before the claim may
be interpreted. This requirement does not enlarge the result-contract arming
precondition or turn such prerequisites into dependency roots.

The `FW_DEVLINK_DT_SUPPLIER_CLOSURE` receipt must preserve:

1. the complete parser-table rows, count, order, source identity, and each
   row's `optional` bit;
2. the effective mode and strict value plus the boot source that establishes
   each;
3. the exact property parser that produced each raw consumer-to-phandle edge;
4. the compatible owning ancestor selected by the fixed kernel;
5. both raw edges and consumer-to-owner edges after the kernel-equivalent
   duplicate elimination;
6. the experiment design's must-bind status for every consumer;
7. the mapped built-in or module provider, exact module bytes, dependency
   order, presence, and expected bind witness; and
8. the final effective probe-blocking decision.

The `DEVICE_INSTANTIATION_CLOSURE` receipt must preserve the dependent device
identity, its exact creator/instantiator identity and expected driver, firmware
parent/child and match evidence, the source call path that performs population
or enumeration, candidate module/built-in and order authority, and the runtime
presence/binding witnesses that make the dependent device available. It must
also distinguish source-proven creation from a device that merely happened to
exist in a stock comparison boot. The combined executability receipt must also
preserve each fixed-point iteration's input frontier, every emitted node and
edge with its producing family, exact-identity deduplication, the convergence
iteration, and proof that every emitted node was offered back to every
registered family.

The `DRIVER_CONSUMED_DT_REFERENCE_CLOSURE` receipt must preserve the consumer
and referenced-node identities, exact DT property and parser call, source
ordering from lookup through the blocking/defer condition, required referenced
driver state, mapped module/built-in and dependency order, and the runtime
presence/bind witnesses. It must fail closed if the relationship is instead
silently attributed to device instantiation or fw_devlink.

The table's `optional` bit never substitutes for must-bind scope. Whether an
optional row is parsed depends on the exact `fw_devlink` mode and
`fw_devlink.strict`; with `on` plus strict true, optional rows are parsed too.
Qualification must evaluate the source condition rather than assigning a
meaning to the field declaration alone.

Changing the global kernel policy to `fw_devlink=off`,
`fw_devlink=permissive`, or a non-strict equivalent is not an admissible remedy
for a missing candidate provider. It changes unrelated device probe ordering,
hides the omitted dependency, and invalidates causal interpretation of a
partially initialized consumer. Add or remove must-bind consumers and satisfy
their exact providers instead.

When `waiting_for_supplier` is used as a live witness, its admissible states
are attribute absent, attribute present with `0`, and attribute present with
`1`. Absence means unavailable authority, not false; the value is a boolean
and never names the unresolved supplier. Existing `supplier:*` device links,
source-derived unresolved candidates, provider presence/binding, and an
independent probe-entry witness must remain separate evidence fields.

### Operator-Attended Observation

The default observation remains unattended and fail-fast. A target-specific,
independently reviewed extension may pause after durable candidate completion
only when its mode, deadline, command allowlist, attempt budget, and handoff
limit were included in the immutable manifest and original F1 approval.

An attended continuation creates no new candidate or partition authority.
Positively classified pre-handoff channel failures may be retried only inside
the original budget and only with proof that no handoff intent or dispatch
occurred. Once handoff intent exists, no observation command may be retried;
the mandatory rollback path remains the only recovery transition.

An attended mode cannot be created after candidate intent or applied to a
consumed run. The selected A90 contract and its implementation closure are in
`docs/operations/A90_F1_ATTENDED_OBSERVATION_V1.md`.

### A90 Resident Boot Promotion

`docs/operations/A90_RESIDENT_BOOT_PROMOTION_V1.md` defines a narrow A90-only
F1-RP terminal for a previously exercised exact candidate. Its original fresh
approval still preauthorizes exact rollback before candidate attempt. Success
requires one candidate transfer and two exact health closures across a separate
resident reboot. Any failure or ambiguity after the candidate attempt starts
uses the ordinary rollback recovery branch.

F1-RP is not selected by the generic S22+ runner, cannot be introduced after
approval, and cannot promote an untested candidate. Its A90-only runner reuses
the existing transfer, journal, and rollback owner and remains non-executable
without a reviewed final manifest and fresh exact approval.

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

For A90 F1-RP, a completed two-boot resident-health closure may close the
candidate as the new experimental baseline without invoking rollback. Before
that exact closure, every post-attempt failure follows the rollback rules
above. After promoted closure, the consumed approval creates no standing
future recovery authority.

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
