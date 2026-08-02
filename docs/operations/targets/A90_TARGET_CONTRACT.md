# A90 Binding Target Contract

Contract-Revision: **1** (supersedes unversioned; 2026-08-02)

Status: **BINDING**

This contract specializes `AGENTS.md` for the operator-owned and attended
Samsung Galaxy A90 5G. It is not authority for S22+, another A90, or an
ambiguous USB endpoint.

`GOAL_A90.md` owns the changing experimental state and next objective. This
file alone neither arms A90 nor opens a D1/F1 campaign. Standing D0 and attended
autonomy apply only through the active common trial and its current live inputs.

## Inheritance and Precedence

Read contracts in this order:

`AGENTS.md -> A90_TARGET_CONTRACT.md -> GOAL_A90.md`

Every common invariant and permanent device, repository, and evidence boundary
in `AGENTS.md` applies. This contract may specialize only the delegated A90
H0/D0/D1/F1 workflow. It cannot relax boot-only payload scope, the forbidden
raw-action list, exact target isolation, rollback availability, candidate
no-replay, private evidence handling, or the requirement for demonstrated
physical recovery. The active common trial controls procedural conflicts;
otherwise the more restrictive applicable rule wins.

The following documents remain implementation references beneath this target
contract:

- `docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md`;
- `docs/operations/A90_F1_ATTENDED_OBSERVATION_V1.md`; and
- `docs/operations/A90_RESIDENT_BOOT_PROMOTION_V1.md`.

They do not independently grant authority. During the common trial, their
stricter v1 state machines are implementation compatibility constraints on
existing runners until changed and tested; they do not narrow trial policy or
require a campaign-level planner.

## Target Isolation

- Resolve exactly one A90 target and its private profile before every D0, D1,
  or F1 action. Keep serials and topology identifiers private.
- When multiple devices are attached, inventory them first, select A90
  explicitly, and report that S22+ and every other target were untouched.
- A90 commands, health evidence, rollback artifacts, approvals, and transport
  identities never apply to S22+.
- Any target ambiguity, unexpected identity change, or lost physical recovery
  path ends the current live session.

## Operating Model

The A90 experiment economy is:

`one F1 resident install -> many attended D1 no-payload experiments`

F1 deploys an exact boot-only native-init candidate and keeps an exact V2321
rollback ready. D1 performs switch-root, return, reboot, display, and service
experiments without another partition payload. A D1 result never qualifies a
new boot image and cannot be used to disguise an F1 action.

Device safety state and experiment proof are separate axes:

| Axis | Results | Meaning |
|---|---|---|
| Device safety | `BASELINE_HEALTHY`, `RESIDENT_HEALTHY`, `RECOVERY_REQUIRED` | Whether the exact A90 remains controlled and recoverable |
| Experiment proof | `PROVED`, `REFUTED`, `NO_PROOF_OBSERVER` | Whether the requested handoff/display/return claim was established |

`REFUTED` and `NO_PROOF_OBSERVER` do not by themselves make a previously
verified resident boot unsafe. Conversely, a visible screen, USB notification,
or parser PASS cannot override a device-safety failure.

## A90 H0

H0 includes source/build work, rootfs and boot-image inspection, deterministic
build checks, parser and framing-codec replay, report generation, and dry runs
with all target access hidden. It grants no device authority.

- Use captured raw logs as a replay corpus. Correct known historical
  misclassifications instead of treating the old verdict as ground truth.
- A host parser, report, or observer failure stops that host invocation, not
  the resident candidate line. Diagnose, repair, and focused-test it at H0.
- Repeating the same observer defect stops that observer implementation until
  repaired; it does not force a candidate flash or rollback.
- A pure parser/classifier update may be recorded per observation without
  invalidating resident boot identity. A change to command dispatch, retry
  count, allowlist enforcement, transfer, or recovery logic requires focused
  safety review and any new binding enforced by the current runner, but still
  does not require an unchanged resident image to be reflashed.

## A90 D0

D0 is exact-target, bounded, connected read-only inspection.

- Permit identity, current native version/build, health, sysfs/procfs, pstore,
  host USB inventory, and existing-file metadata reads with explicit bounds.
- Do not reboot, hand off, enter recovery, start or stop a service, mutate a
  file or setting, or send a payload.
- A D0 observer failure closes only that read. It creates no D1/F1 authority
  and does not make an otherwise controlled resident unsafe.
- With more than one attached device, name A90 as the selected target and
  explicitly confirm S22+ received no command.

## A90 D1 Attended Session

The namespaced risk label is `TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL`. Historical
server-distro stage names such as `STAGE_D1_CHROOT_MVP` are not risk labels.

Under the active trial, the agent selects and iterates exact allowlisted D1
effects while attendance and `HEALTHY` hold. Policy imposes no per-action
approval or action/time budget. The existing v1 runner still opens one fresh
`A90_D1_ATTENDED_SESSION_V1` and enforces the compatibility bounds below.

**Attendance predicate.** For a bound `RESIDENT_HEALTHY` A90 with a proved
working return channel, the operator must be present and able to stop D1;
physical Download entry is not required. A90 F1 uses the stronger predicate:
the operator must be able to perform physical recovery entry.

An absent or late ACM/NCM endpoint after an announced A90 transition enters the
common `HEALTH_PENDING` classification; it is not by itself target ambiguity or
resident-health failure. The runner may repeat passive inventory and bounded
health reads, stabilize a changed USB epoch, repair a host-only observer, or
park for predeclared recovery. It must not start a new ordinal action until the
exact resident is `HEALTHY`, and it must never resend the uncertain action.

The legacy v1 session binding must contain:

- the exact A90 target/profile and current resident boot identity;
- the exact ready rollback identity and recovery path;
- an exact command/action allowlist;
- an explicit positive duration no greater than eight hours; the immutable
  host template does not expire before use, and the runner durably fixes the
  exact opening and expiry timestamps only when it consumes the fresh session
  approval;
- an explicit positive action budget no greater than 32; and
- the return-health predicate and device-effect runner closure.

The legacy v1 runner rules are:

1. Announce each action, send it once to the exact A90, append one compact
   action result, and decrement the action budget. No blind automatic loop is
   permitted.
2. Allow only transient actions named in the binding, such as native-init UI
   hide/show, one switch-root handoff, one bounded native return or reboot, and
   transient start/stop of an already-installed Debian experiment service.
3. Forbid partition payloads, arbitrary shell expansion, persistent settings,
   credential changes, security-state changes, package installation, rootfs
   replacement, and recovery-path mutation.
4. Expected USB disconnect/re-enumeration during an announced reboot or
   handoff is an observation, not by itself a failure.
5. End the session on expiry, budget exhaustion, operator absence, target or
   resident identity change, lost rollback/recovery, an unallowlisted effect,
   explicit operator stop, or a device-safety failure.

If framing, timeout, or parsing fails after an action but the previously
verified resident remains operator-controlled and an independent bounded check
can distinguish observer failure from device failure, close that experiment
`NO_PROOF_OBSERVER`. Never automatically resend the uncertain device action.
After exact cleanup and resident health, the operator may explicitly
acknowledge that result and start one new ordinal action with the unchanged
observer, or fix/replace the observer at H0. An acknowledgement is not a replay:
it requires a new durable intent and consumes another action. A second
observer-only no-proof after that unchanged-observer acknowledgement closes the
session. Continue only while target, resident, rollback, allowlist,
device-effect runner, expiry, and remaining budget are unchanged.

If observer failure cannot be distinguished from target ambiguity, control
loss, or resident-health failure, end the session and select the predeclared
recovery path. The same confirmed device-effect failure twice stops live A90
experimentation; the same host parser defect twice stops only that parser
implementation.

## A90 F1 Resident Install

A90 F1 uses the checked `native_init_flash.py` path and may transfer only the
exact boot candidate or its exact V2321 rollback. TWRP/Download is a
preflight-proven recovery environment, not permission to write the recovery
partition or any non-boot partition.

Before any F1 effect, prove the exact healthy A90 starting state, exact candidate
and rollback regular files and SHA256 values, boot-only membership, exact
rootfs input and work-copy disposition when applicable, an empty durable
journal, checked flash/bridge closures, and physical recovery availability.

Trial policy needs no per-candidate approval, but the existing v1 runner still
requires one fresh `A90_F1_RESIDENT_INSTALL_V1` binding for one candidate plus
its exact rollback. Candidate replay is forbidden: the runner must never retry
the candidate. Once candidate execution begins, rollback never waits.

After the candidate transfer:

- candidate transfer ambiguity, wrong identity, explicit initial-health
  failure, inability to establish initial control, or lost recovery requires
  exact rollback;
- initial resident health requires exact candidate version/build, the bound
  native self-test/health predicates, a working bounded control response, and
  preserved physical recovery; and
- once `RESIDENT_HEALTHY` is durably recorded, a later Debian experiment
  refutation or observer-only no-proof does not retroactively fail installation
  and does not require rollback.

A successful install terminal is `PASS_A90_RESIDENT_INSTALLED`. A failed or
ambiguous install uses one exact rollback and closes only after V2321 health is
verified. A rollback failure is `RECOVERY_REQUIRED`. The existing v1 runner's
first use of this terminal requires its schema update, focused tests, review,
connected preflight, and compatibility binding; this document alone creates no
active campaign.

## Attended F1 Pre-Handoff

The existing reviewed attended pre-handoff exception remains narrow. It may
retry only a positively proven channel-input failure before any handoff intent,
inside the predeclared deadline and attempt budget. The runner must durably
record handoff intent before dispatch. After that point, it never retries the
handoff or candidate. This F1 exception is separate from the post-install D1
attended session.

## Evidence and Reporting

- Routine D0 needs only the bounded read result.
- Routine D1 uses one session record plus compact ordered action entries; it
  does not require one policy, manifest graph, prose report, or review ladder
  per action.
- A resident-install terminal may be reduced once to one immutable resident
  baseline binding. Routine D1 preparation derives its canonical journal from
  that resident manifest; the operator must not select a second independent
  journal path.
- F1 uses one structured result, one append-only journal, private raw logs, and
  a compact target-specific timeline. Record exact candidate/rollback transfer
  counts and no-replay status.
- A parser or reporting failure after a proven transition never repeats that
  transition.
- Write prose only for a policy change, new capability/hazard, incident,
  recovery deviation, or genuinely ambiguous device-safety result.

## Review and Change Control

- Changes to this binding target contract require one independent safety
  review.
- Review must confirm common boot-only, forbidden-action, exact rollback,
  no-replay, target-isolation, physical-recovery, and private-evidence rules
  remain intact.
- Review execution machinery only when its device-effect, transfer, recovery,
  schema, or hazard closure changes. Parser-only H0 repairs need focused tests,
  not a new F1 review ladder.
- Keep current candidate hashes, consumed approvals, run IDs, and experimental
  frontier in `GOAL_A90.md` or private evidence, not in this stable contract.
