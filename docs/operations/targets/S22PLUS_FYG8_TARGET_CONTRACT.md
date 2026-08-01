# S22+ FYG8 Binding Target Contract

Status: **BINDING**

This contract specializes `AGENTS.md` for the attended Samsung Galaxy S22+
FYG8 target `SM-S906N` / `g0q` / `S906NKSS7FYG8`. It is not authority for any
other model, firmware, target profile, or connected device.

`GOAL.md` owns the current experimental state. This document contains stable
operating rules only. Neither this document nor a policy refactor grants live
device authority.

## Inheritance and Precedence

All common invariants and permanent safety boundaries in `AGENTS.md` apply.
This contract may specialize the delegated H0/D0/D1/F1 and pre-session failure
rules only. Where texts differ, the more restrictive applicable rule wins.

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
  bundle binds their exact bytes. Such a repair must prove `CHANGED_KEYS=[]`
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
5. Every step intended for a later approval window must first be exercised
   outside that window with the real existing input or, when live input cannot
   exist yet, a captured representative fixture. Do not make approval-time
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

- Require a fresh approval binding the exact target, command, bound, recovery
  contingency, and return-health check.
- Permit no partition payload, persistent setting, security-state change, or
  cross-target command.
- Send the approved action once. An unexplained failure after it begins stops
  D1. Do not turn it into a retry loop or an F1 substitute.
- Predeclare any attended hardware-restart contingency and its trigger. Do not
  invent a recovery action during the session.
- Verify and report the expected healthy terminal state.

## S22+ F1

S22+ F1 is the ordinary Process-v2 boot-only candidate transfer followed by
its mandatory exact rollback and verified final health.

- Use Odin with ordinary regular `.tar.md5` paths. Each candidate and rollback
  AP must contain exactly one regular `boot.img.lz4` and no forbidden member.
- Require a new immutable manifest, exact connected preflight/D0, and one fresh
  approval binding the target, candidate, rollback, manifest, and runner
  closure.
- The approval authorizes one candidate attempt and its necessary rollback.
  Never replay or retransmit the candidate. Once candidate execution begins,
  rollback does not wait for another approval.
- Journal before invoking Odin and after every state transition. Recover only
  from durable journal state.
- A host rejection or local parser failure that is positively proven to occur
  before Odin begins or reports a device session is a pre-session H0 failure,
  not a candidate attempt. Apply the bounded Rule-7 rule above. Any repaired
  execution-critical closure requires a new exact approval binding before live
  use. Tool-process creation alone is not proof that a device session started.
- Once Odin identifies or contacts the device, Download handoff starts, or any
  device command is sent, an unexplained failure is an immediate stop. Only the
  already-authorized exact rollback path may continue; the candidate may not.
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
  qualification and approval, not a new policy ladder.
- This target contract may be made more precise without copying current
  campaign state into it. Put changing frontier and authority state in
  `GOAL.md`.
