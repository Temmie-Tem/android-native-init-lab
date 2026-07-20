# Device Action Process v2

Status: P2.1-P2.4 complete; reusable F1 adapter and canary pending.

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
The F1 adapter must reuse this core rather than add a candidate-specific runner.

The F1 adapter will own:

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
escalate recovery. Do not launch a second candidate. A stock boot cleanup path,
when a target profile supports one, is recovery-only and cannot produce PASS.

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
read-only qualification. P2.5 may now implement the reusable F1 adapter
host-only. No F1 run is authorized until that execution-critical closure passes
independent review and the operator gives one fresh approval for the exact
binding.
