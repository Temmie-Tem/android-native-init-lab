# S22+ FYG8 Binding Target Contract

Status: **BINDING**

This contract specializes `AGENTS.md` for the attended Samsung Galaxy S22+
FYG8 target `SM-S906N` / `g0q` / `S906NKSS7FYG8`. It is not authority for any
other model, firmware, target profile, or connected device.

`GOAL.md` owns the current experimental state. This file alone neither arms the
target nor opens a D0/D1/F1 action. The common Fast-Loop trial is retired; it
grants no standing D0, attended autonomy, or per-candidate approval waiver.

## Inheritance and Precedence

All common invariants and permanent safety boundaries in `AGENTS.md` apply.
This contract may specialize delegated H0/D0/D1/F1 and pre-session failure
rules only. The retired common trial is historical evidence and resolves no
procedural conflict; the more restrictive applicable live rule wins.

The ordinary S22+ F1 mechanism is
`docs/operations/DEVICE_ACTION_PROCESS_V2.md`. Full-stock evidence under
`docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`
is recovery evidence only and never authorizes full-firmware or non-boot
flashing. Historical `DRAFT`, `EXCEPTION`, `ACTIVE_CLAUSE`, and archived files
do not grant authority.

## Target Isolation

- Resolve the exact S22+ target and target profile before every D0, D1, or F1
  action. Device serials remain private.
- When multiple devices are attached, inventory them first, select the exact
  S22+ explicitly, and record that every other device was untouched.
- Any ambiguity between S22+, A90, transport endpoints, Download-mode devices,
  or rollback identities is an immediate stop.
- A90 approvals, health evidence, transports, artifacts, and resident-promotion
  rules never apply to S22+.

## S22+ H0

H0 includes source and artifact inspection, intent and contract design,
building, Full-LTO A/B, static and linked audits, package construction,
offline promotion, manifest construction, and dry runs with all device access
hidden. H0 may create private payload artifacts but grants no right to use
them on a device.

### Source identity

- Before intent derivation, freeze the complete byte-affecting change list and
  print the selected `SOURCE_KEYS` with their paths. Compare them against
  Git-derived tracked and untracked changes in both directions.
- After intent derivation, do not change a `SOURCE_KEYS` byte. A Tier-1 change
  invalidates the run identity and requires a new intent and qualification,
  including a new Full-LTO A/B pair when applicable.
- Verifiers, decoders, evidence adapters, and documents may remain outside
  candidate identity only when the selected contract says so and the approval
  or live-binding bundle pins their exact bytes. Such a repair must prove `CHANGED_KEYS=[]`
  and cannot alter the candidate artifact.
- Never repair repository files while Full-LTO is running. Stop the build and
  report the proposed edit first.

### S22+ Rule 7: bounded pre-session repair

A material failure is identified by its failed invariant, input/producer
contract, and causal mechanism, not merely by exception spelling or line
number.

Before any connected device command is sent and before a transfer tool begins
or reports a device session:

1. The first novel material host-only failure stops that invocation, preserves
   its evidence, and permits one bounded H0 diagnosis, one scoped repair, and
   one corrected execution of the failed bounded unit.
2. The repair must cite the observed input or fixture, the exact changed
   closure, and why candidate identity is preserved or invalidated. It must run
   focused validation before the corrected execution.
3. The same material failure a second time stops the line of work. Renaming an
   exception, moving the failure, or changing only its representation does not
   make it novel.
4. Distinct novel failures receive separate signatures, but this rule never
   authorizes retry-until-pass loops, speculative repeated builds, or a device
   action.
5. Every step intended for a later live window must first be exercised outside
   that window with the real input or, when live input cannot exist yet, a
   captured representative fixture. Do not make attended live
   execution the first execution of host code.

H0 request hashes and re-entry packets are evidence bindings, not device
authority. Do not make them stricter than this rule by default. A particular
operator authorization may deliberately impose a narrower stop condition; if
so, that narrower text controls that invocation.

After the first connected device command, Download-mode handoff, or transfer
tool device session begins, the common immediate-stop rule applies. No bounded
host repair in this section can be used to continue the live candidate.

## S22+ D0

D0 is bounded, connected, read-only observation of the exact S22+ target.

- Use explicit target selection and bounded commands. Reads may include exact
  identity, boot health, sysfs/procfs state, and host USB inventory.
- Do not reboot, alter modes or settings, create device files, restart a
  service, write sysfs, or send a payload.
- A D0 ambiguity or unexplained failure ends that D0 invocation. It grants no
  F1 authority and does not consume or replay a candidate transfer.
- With multiple attached devices, report the selected S22+ and explicitly
  confirm that the other target received no command.

## S22+ D1

D1 is one exact, transient, no-payload control action.

**Attendance predicate.** The operator must remain present and able to perform
the action's predeclared return or recovery step. If the action can remove the
working control channel or require a physical restart, the operator must be
able to perform that physical step within its bound. Attendance loss freezes
new effects; it never authorizes replay of the uncertain action.

- D1 requires the fresh exact authority specified by the live common and target
  rules. Any helper binding of target, command, recovery, and return health is
  an additional compatibility constraint and never substitutes for authority.
- Permit no partition payload, persistent setting, security-state change, or
  cross-target command.
- Send the bound action once. An unexplained failure after it begins stops
  D1. Do not turn it into a retry loop or an F1 substitute.
- Predeclare any attended hardware-restart contingency and its trigger. Do not
  invent a recovery action during the session.
- Verify and report the expected healthy terminal state.

## S22+ F1

S22+ F1 is the ordinary Process-v2 boot-only candidate transfer followed by
its mandatory exact rollback and verified final health.

**Attendance predicate.** For S22+ F1 the operator must be able to perform a
physical Download entry within the profile's recovery bound, not merely be
present. A run awaiting that physical step parks, remains F1-armed, and resumes
from durable journal state. Host-only work continues during the park.

Endpoint absence or late host discovery during that interval enters
`HEALTH_PENDING` and then `RECOVERY_PENDING_PARKED`; it is not by itself a
candidate, device-health, or recovery failure. No next candidate may be armed
and the uncertain candidate is never replayed. Passive host observation and
the exact predeclared rollback continue until final FYG8 health is proved or
the predeclared recovery path is exhausted.

**Physical-topology continuity.** From the exact Download endpoint binding
through rollback transfer and verified final-health close, the operator must
not disconnect, move, or reroute the data cable, dock, or host port. The
observer must never widen its selector or open an unapproved endpoint.

This is the permanent `S22PLUS_F1_PHYSICAL_TOPOLOGY_CONTINUITY` boundary. It
blocks physical endpoint drift from invalidating candidate attribution or
rollback authority, applies only to S22+ F1 endpoint observation and recovery,
and has no expiry. Any change to endpoint identity, topology/controller
capture, phase classification, recovery rebinding, or selector semantics
requires a new independent boundary review.

Process-v2 evidence must retain the exact endpoint identity, topology, host
controller/device path, and immutable raw-snapshot receipt at approved Download
start and candidate-observer closure. Before rollback transfer it must retain a
fresh exact Download/rollback binding with the same fields. A normal unchanged
path is `rollback_bound_exact`: it is a fresh revalidation of the original
predeclared rollback authority and does not require a new independent recovery
review. A missing, truncated, or unreadable snapshot is an observer failure,
not proof of path continuity.

Classification is phase-specific. A non-exact Download-start binding is a
pre-session stop and has no consumed-run proof class. Candidate-end drift is
`NO_PROOF_EXPERIMENT_PRECONDITION`, but an exact, complete same-path observer
window with no host endpoint remains eligible for the experiment's declared
host-silent device-result classification. Rollback-endpoint drift or absence
parks recovery and never changes an already retained experiment result.

For a P3.18 timing successor, “no host event” is not a default value. It is
admissible only when an exact DWC3 event latch was registered and read back as
armed before gadget exposure, its install sample is valid and no later than
the diagnostic `pre` sample, and the complete candidate-end host receipt has
no endpoint. An endpoint-present receipt combined with an armed no-event mask
is an observer contradiction. An incomplete or unavailable host receipt is an
observer failure and can never support a no-event claim. An armed host event
combined with a complete no-endpoint receipt is the distinct
`DEVICE_RESULT_DWC3_HOST_EVENT_NO_ENDPOINT`, not a host-silent result. A
missing install sample means “host event not observable,” never “no host
event,” and cannot support a MUX ordering claim.

A drifted topology does not authorize rollback against the new path. Mandatory
rollback remains required, but the run parks without new device effects until
a bounded, independently reviewed recovery-only path establishes
`recovery_rebound_exact` for one exact current rollback endpoint under a new
immutable recovery binding ID. Only then may the predeclared exact rollback
resume from durable journal state. The new binding may name a different
physical path; it is recovery authority only and does not retroactively
validate candidate attribution. `rollback_bound_exact` and
`recovery_rebound_exact` are distinct authority states; the latter cannot be
inferred from an ordinary fresh rollback revalidation. Candidate replay
remains forbidden.

- Use Odin with ordinary regular `.tar.md5` paths. Each candidate and rollback
  AP must contain exactly one regular `boot.img.lz4` and no forbidden member.
- Process-v2 requires a new immutable manifest, exact D0, one fresh
  candidate/rollback binding, and the fresh exact approval required after
  Fast-Loop retirement. No retired trial clause waives per-candidate approval.
- One candidate intent covers only that attempt and its exact rollback.
  Never replay it. Once candidate execution begins, rollback does not wait.
- Journal before invoking Odin and after every state transition. Recover only
  from durable journal state.
- A host rejection or local parser failure that is positively proven to occur
  before Odin begins or reports a device session is a pre-session H0 failure,
  not a candidate attempt. Apply the bounded Rule-7 rule above. Any repaired
  execution-critical closure requires a new exact legacy-runner binding before
  live use. Tool creation alone is not proof that a device session started.
- Once Odin identifies or contacts the device, Download handoff starts, or any
  device command is sent, an unexplained failure is an immediate stop. Only the
  predeclared exact rollback path may continue; the candidate may not.
- Candidate boot or Odin success alone is not PASS. PASS requires the intended
  bounded observation, exact rollback, and verified healthy stock terminal
  state.

## Evidence

Routine D0/D1 evidence is proportional to the action. F1 uses one structured
result, one append-only journal, private raw logs, and the Process-v2 canonical
event order:

`live_session_start -> candidate_flash_start -> candidate_flash_done -> candidate_boot_ready -> rollback_flash_start -> rollback_flash_done -> rollback_boot_ready -> live_session_end`

Normal Android boot and absence of a boot loop are operator observations, not
formal proof by themselves. Preserve bounded observer evidence, exact transfer
counts, no-replay status, rollback result, and target-specific health closure.

## Review and Change Control

- Changes to this binding contract require one independent safety review.
- Review must check that boot-only, rollback availability, no replay, target
  isolation, post-session immediate stop, and private-evidence rules remain
  intact.
- Re-review execution machinery only when its execution-critical closure or
  hazard class changes. A new candidate with unchanged machinery needs fresh
  qualification and any legacy runner binding, not a new policy ladder.
- This target contract may be made more precise without copying current
  campaign state into it. Put changing frontier and authority state in
  `GOAL.md`.
