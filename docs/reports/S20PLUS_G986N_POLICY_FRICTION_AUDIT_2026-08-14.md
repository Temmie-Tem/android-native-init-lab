# S20+ G986N policy-friction audit

Status: **H0 REVIEW AND RECOMMENDATION ONLY - NO POLICY ACTIVATION**

Date: 2026-08-14

Target: operator-owned Samsung Galaxy S20+ 5G, exact public identity
`SM-G986N` / `y2q` / `G986NKSS8IYC2`

This report reviews the current S20+ control surface for proportionality and
future experimental usefulness. It does not amend `AGENTS.md`, the binding
target contract, a runner, a guard, or a live approval. No ADB, USB endpoint,
Odin, reboot, or device command was used for this audit. Existing policy
remains binding until a separately reviewed amendment is activated.

## Executive conclusion

The permanent device boundaries are mostly well chosen. Exact target
selection, boot-only archive membership, an exact stock rollback, one
candidate attempt, no replay after transfer intent, private raw evidence, and
final stock health materially prevent the failure modes that can brick or
misidentify a device. They should remain.

The present S20+ implementation is nevertheless over-managed before a
partition transfer begins. It gives a Download transition, a failed endpoint
observation, and a completed Odin transfer nearly the same guard lifetime and
incident-repair burden. That is why an ordinary request to return the phone to
normal Android can require a new helper, hard-coded historical hashes, a new
review, and another exact token even when the journal proves that no candidate
intent or Odin transfer exists.

The immediate design correction is not to weaken flash safety. It is to create
a first-class `PRE_CANDIDATE_ABORT` state and let the owner of the existing F1
guard perform one payload-free normal return under that same guard. After exact
Android health, a generic durable finalizer closes the run. Candidate no-replay
rules begin only when candidate transfer intent is durable.

## Current policy map

| Class | Current S20+ capability | Assessment |
|---|---|---|
| H0 | artifact/source inspection, builders, parsers, tests | proportional |
| D0 | exact public-property reads and one grammar-bounded patched-AP retrieval | mostly proportional; onboarding one-shot guard is historical baggage |
| D1 | APK install, fixed AP stage, normal/Download/recovery reboot, payload-free Download exit | action set is reasonable; guard, handoff, token, and evidence requirements are too heavy for no-payload control |
| F1 | one boot-only Magisk candidate, bounded root observation, mandatory stock-boot rollback | appropriate as a first qualification, but cannot itself produce resident root or advance native-init |
| X | recovery/TWRP, VBMeta, BL, CP, CSC, DTBO, super, userdata, EFS, raw block and fuse operations | retain as permanent exclusions unless the repository deliberately adopts a separately reviewed wider risk boundary |

## Current concrete blocker

Host-only inspection found one unresolved shared S20+ action guard bound to the
current F1 run. Its durable result requests candidate-endpoint confirmation.
The run contains the initial Download baseline, intent, observation, result,
prepared record, endpoint-re-enumeration record, and result. It contains no
candidate intent, candidate result, or candidate Odin stdout/stderr evidence.

Therefore the current state proves:

- one Android-to-Download control transition occurred;
- candidate partition-transfer commands recorded by the F1 journal are zero;
- candidate replay is not the issue because candidate execution never began;
- the standalone `exit-download` helper cannot arm because the shared guard is
  already owned by the F1 run that needs the return action; and
- the public goal and activation prose saying that no run exists is stale.

This is a state-model defect, not evidence that the device is unresponsive and
not a reason to weaken post-transfer rollback or no-replay rules.

## Live-document consistency findings

The current public documents mix current rules with historical snapshots. The
following contradictions should be corrected as part of P1, but they do not by
themselves authorize a device action:

- the target-contract heading says only `D0 ONBOARDING CONSUMED` while later
  sections and the registry activate routine D0/D1 and attended F1;
- the target contract's routine table contains six D1 actions, but its later
  summary says that five are defined;
- the goal retains an early
  `FORMAT_COMPATIBLE_AVB_AND_TRANSPORT_UNQUALIFIED_NO_GO` and “no patched image
  was created” snapshot, although later entries record the retrieved patched AP,
  constructed boot-only candidate/rollback APs, and an active F1 capability;
- the goal and activation record say no run is prepared or approved, while the
  private shared guard currently points to an unresolved F1 run; and
- successive dormant, suspended, corrected, active, and incident-specific
  hashes are accumulated in the binding contract, making it difficult to
  identify the one current execution closure.

A binding contract should state only the current machine and immutable safety
rules. Historical verdicts and superseded hashes belong in dated reports. A
machine-generated, privacy-preserving status line should be the single source
for whether a current guard/run exists.

## Controls to retain

These controls have a direct device-safety or target-isolation benefit and
should survive any simplification:

1. Select the exact `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2` Android
   target immediately before a connected Android command. Never transfer an
   S20+ approval, artifact, endpoint, or recovery identity to S22+ or A90.
2. Permit only a deterministic AP whose sole regular archive member is
   `boot.img.lz4`. Continue rejecting recovery, VBMeta, DTBO, BL, CP, CSC,
   super, persist, userdata, EFS, and every other partition member.
3. Pin candidate and stock rollback bytes by path, size, SHA-256, and archive
   membership before the first candidate transfer.
4. Require an attended, causally observed Download endpoint and pin its current
   character-device identity immediately around each Odin dispatch.
5. Write durable intent before a partition-transfer attempt. After candidate
   intent, permit no candidate replay, including when Odin output is missing or
   ambiguous.
6. Keep the stock rollback preauthorized once candidate execution starts. Do
   not wait for another approval before required rollback.
7. Require exact Android identity and health after rollback before releasing
   the experiment guard or starting another flash experiment.
8. Keep serials, raw USB topology, boot IDs, firmware, images, and raw command
   output under `workspace/private/`.
9. Require independent review when execution-critical transfer, archive,
   recovery, target-selection, or hazard behavior changes. Reuse that review
   for unchanged runners and hazard classes.
10. Before the first custom boot, obtain one explicit operator decision about
    the possibility of an irreversible Knox warranty/security-state change.
    The photographed `WARRANTY VOID: 0x0` is a starting observation, not a
    guarantee that it remains zero after a custom binary.

## Controls that are disproportionate

| Current control | Why it obstructs the experiment | Recommended replacement |
|---|---|---|
| One shared guard blocks every S20+ action, including recovery of its owning run | a safe normal-return action cannot repair the exact run holding the guard | owner-aware guard: block new experiments but allow only the current run's reviewed observation, rollback, or payload-free abort path |
| Pre-candidate endpoint failure retains an F1 incident indefinitely | no candidate intent and no Odin evidence means no partition effect occurred | terminal `PRE_CANDIDATE_ABORT`; one no-payload return if needed, exact health, durable closure, release |
| Separate hard-coded finalizers for individual historical run hashes | each ordinary pre-effect incident creates code, policy text, tests, hash rotation, and review | one schema-versioned generic finalizer that validates invariant state and exact guard ownership rather than a named incident |
| Prepare-time USB inode/devnum must survive Download re-enumeration | Linux USB device nodes are expected to change across reboot/re-enumeration | bind empty baseline, one causal arrival, stable topology/profile, operator attendance, and the fresh endpoint identity immediately before and after dispatch |
| Expected endpoint re-enumeration needs another magic confirmation token | the operator already approved one attended candidate and no new artifact/effect is introduced | keep one fresh F1 approval at the candidate-intent boundary; absorb bounded expected re-enumeration into the same guarded invocation |
| Standalone Download exit always requires unplug, empty baseline, reconnect, and token | this repeats causality already proved by a same-run Android-to-Download transition | reuse the owning run's transition evidence; require physical empty-baseline handoff only for an orphaned or manually entered Download session |
| Routine D1 uses F1-grade exact-node/no-extra-node journal defenses | the common threat model explicitly excludes a malicious same-UID owner between syscalls | for no-payload D1, retain guard ownership, no-clobber intent/result, bounded argv/output, and final health; reserve adversarial archive/journal closure for F1 |
| Routine no-payload return checks root absence | root absence is not the terminal property of an ordinary reboot or Download exit | require exact normal Android health; require root absence only for stock-rollback closure or a test whose objective is root absence |
| Runner self-hash is copied into several prose documents and exact-string tests | harmless wording or mechanical activation causes hash churn and repeated closure work | one versioned capability manifest containing execution-critical hashes; contracts and tests refer to the manifest semantically |
| Live contract contains successive activation and incident narratives | current rules, historical state, and stale “no run” claims conflict | keep the live contract concise; archive incident records and generate one current-state summary from the guard/journal |
| Every uncertainty tends to produce a new reviewed helper | management work grows faster than experimental evidence | add new review only for a new effect or hazard; handle already-modeled states through a generic state machine |

## Recommended state model

The useful boundary is candidate transfer intent, not merely entering Download
mode:

```text
HEALTHY_ANDROID
  -> PREPARED
  -> DOWNLOAD_OBSERVED
       -> PRE_CANDIDATE_ABORT
            -> PAYLOAD_FREE_NORMAL_RETURN
            -> HEALTHY_ANDROID / CLOSED
       -> CANDIDATE_INTENT_DURABLE
            -> CANDIDATE_ATTEMPTED          (never replay candidate)
            -> OBSERVE_ROOT_OR_NO_PROOF
            -> ROLLBACK_INTENT_DURABLE      (preauthorized)
            -> STOCK_ROLLBACK_ATTEMPTED
            -> STOCK_HEALTHY / CLOSED
            -> RECOVERY_PENDING             (guard retained)
```

Rules for the simplified machine:

- Before `CANDIDATE_INTENT_DURABLE`, all failures are zero-partition-effect
  failures. A fresh invocation may repeat host preflight, or the current guard
  owner may abort to normal Android.
- Writing candidate intent consumes the one candidate attempt. Missing logs,
  timeout, parser failure, disconnect, and ambiguous completion never permit a
  second candidate transfer.
- A reboot or Download request is not replayed merely because observation is
  late. The same guard may continue bounded observation or invoke its one
  payload-free return path.
- The guard excludes competing experiments, not the recovery operations of its
  own state machine.
- Every terminal path writes its result before guard release.

## Future technical blockers

Policy simplification will improve iteration speed, but it will not remove
these real technical constraints:

1. **AVB/VBMeta compatibility.** The stock boot AVB footer and the separate AP
   `vbmeta.img` bind the stock boot digest. If the boot-only Magisk candidate
   cannot boot with unchanged VBMeta, the current permanent boot-only boundary
   makes this rooting route a genuine `NO_GO`; it must not be papered over by
   flashing the official full patched AP.
2. **Knox and device security state.** The device currently shows Samsung
   Official and warranty void `0x0`, but a custom boot can create an
   irreversible state change. This needs a deliberate operator decision before
   the first actual candidate transfer.
3. **KG and Secure Download behavior.** `KG STATUS: CHECKING` and `SECURE
   DOWNLOAD: ENABLE` may reject or constrain the custom boot. Only a bounded
   live candidate attempt can resolve that uncertainty.
4. **Odin boot-only acceptance.** Offline archive validation proves format and
   membership, not that the device accepts a one-member boot AP or that the
   stock one-member rollback works on this exact bootloader revision.
5. **ADB-less candidate failure.** If the custom boot never exposes exact
   Android/ADB health, attended physical Download recovery must remain usable.
6. **Magisk observation semantics.** A booted candidate may need bounded time
   or app-side completion before `su` appears. The observer must distinguish
   delayed initialization from transport failure without replaying the boot.
7. **Resident-root gap.** The active bootstrap always restores stock boot, so
   even a successful result deliberately leaves no resident root. Native-init
   development needs a separate resident-promotion capability after bootstrap
   qualification.
8. **Kernel reproducibility.** The exact final stock configuration is known,
   but the Samsung/Qualcomm toolchain, reproducible kernel bytes, boot packing,
   and signature behavior remain unproved. `CONFIG_MODULE_SIG_FORCE=y` may also
   block arbitrary external modules.
9. **Recovery/TWRP scope.** TWRP writes recovery and remains outside the current
   permanent boundary. Root/native-init work must use boot-only mechanisms
   unless that boundary is deliberately reconsidered in a separate review.
10. **Firmware drift.** Any firmware change invalidates the exact build profile,
    artifact hashes, and possibly the Download/AVB assumptions.

## Recommended implementation order

### P0 - unblock safe recovery without widening flash authority

Implementation status: **independently reviewed, active**. The runner exposes
`--abort-pre-candidate`. The device returned to Android and the guarded run
completed its zero-Odin health-only branch; the terminal receipt records zero
partition transfers and the owning guard is released.

1. Add one generic `abort-pre-candidate` path to the F1 runner.
2. Require the matching active guard, the exact initial transition journal,
   and absence of candidate intent/result/raw Odin evidence.
3. If already in exact healthy Android, write the close result and release the
   guard. If still in Download, issue one payload-free Odin reboot under the
   same guard, then require exact Android health before release.
4. Treat the user's direct attended request as the D1 approval; do not require
   a candidate or rollback token for this zero-payload action.
5. Add fixtures for extra/forged candidate evidence, foreign endpoint,
   ambiguous endpoint, Odin uncertainty, unhealthy Android return, and second
   invocation. None may create a partition transfer.

This P0 change should replace, then retire, the run-specific
`--close-pre-candidate` and `--close-endpoint-uncertain` branches after their
historical receipts are preserved.

### P1 - simplify the reusable control plane

1. Make the shared guard owner-aware and encode the state above.
2. Replace long-lived endpoint inode equality with causal baseline/arrival plus
   dispatch-time endpoint pinning.
3. Merge ordinary no-payload controls into one routine D1 implementation and
   one result schema.
4. Move execution-critical identities to a single reviewed capability
   manifest; stop copying mutable runner hashes through several prose files.
5. Generate current active-run status from private guard metadata so public
   documents do not claim “no run” while a guard exists.
6. Archive superseded activation narratives rather than accumulating them in
   the live binding contract.

P1 is complete when a pre-candidate failure can be closed without a new
incident-specific helper or review, while all post-intent no-replay and
rollback fixtures still pass.

### P2 - make the path useful for native-init work

After one boot-only bootstrap proves candidate transfer, root observation,
physical recovery, and stock rollback, define a separate resident-promotion
F1 capability. It should retain the exact candidate only after explicit
operator approval and multiple independent health closures, including a
separate normal reboot. Any failure keeps the exact stock rollback mandatory.
That is a new execution capability and needs one independent review; it should
then be reusable for unchanged candidate and hazard classes.

Native-init iteration after resident promotion should use a bounded resident
D1 lane for exact files/services needed by the experiment. It should not
require another Odin flash for every edit.

## Operator decisions

1. The permanent partition scope remains boot-only. TWRP, VBMeta, BL, CP, CSC,
   and other partition writes remain excluded.
2. On 2026-08-14 the operator explicitly accepted the possible irreversible
   Knox warranty/security-state change from the first custom boot. This
   decision applies to this S20+ bootstrap campaign and need not be requested
   again while the target and hazard class remain unchanged.
3. P0 owner-aware same-run payload-free abort is reviewed, active, and its
   first guarded closure completed with zero partition transfers.
4. The intended sequence is bootstrap qualification followed by a separately
   reviewed resident-promotion capability for the native-init objective.

## Acceptance criteria for a policy amendment

A follow-up change may be considered proportionate when it proves all of the
following:

- permanent target, boot-only, rollback, no-replay, privacy, and final-health
  boundaries are unchanged;
- pre-candidate and post-candidate states are mechanically distinct;
- the current guard owner can recover or abort without opening a second action;
- no-payload D1 uses one direct request and one durable result rather than an
  incident-specific approval graph;
- an unchanged reviewed capability is reusable across runs;
- expected USB re-enumeration does not itself consume the experiment;
- candidate intent remains the irreversible no-replay boundary; and
- S22+ and A90 files, profiles, approvals, devices, and commands remain outside
  the change.
