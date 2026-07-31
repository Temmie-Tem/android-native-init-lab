# A90 Resident Boot Promotion v1 H0 Runner

Date: 2026-08-01 KST

Result: `PASS_H0_RUNNER_REVIEWED_NO_LIVE_MANIFEST`

## Outcome

The A90-only resident-promotion runner is implemented and independently
reviewed. It grants no device authority. No device, USB endpoint, network
interface, candidate transfer, rollback transfer, reboot, cleanup, or connected
preflight occurred in this unit. Exact V2321 remains resident.

The implementation does not introduce a second flash or recovery engine. The
existing V3403 orchestrator remains the sole owner of absent-only staging,
boot-only candidate transfer, append-only journal, and exact rollback. The new
runner supplies only the manifest validator and the resident reboot plus second
health tail.

## Closed execution contract

Before approval or candidate intent, the runner requires:

- the exact manifest-bound runner and Debian A/B qualification helper;
- a prior final Process-v2 manifest, prepared approval, contiguous journal,
  result, and canonical timeline;
- reconstruction of the prior canonical approval binding;
- the same A90 bridge path and recovery-identity digest as the new target;
- one prior candidate transfer, one exact rollback, and no replay;
- exactly parsed raw candidate and V2321 version/selftest lines; and
- the exact corrected deterministic 2 GiB Debian A/B input.

The success tail requires two exact candidate health closures on distinct USB
epochs. The returned A90 ModemManager guard is revalidated after the second
health command set and again before durable resident-health intent. Promotion
events are available only through the explicit manifest-bound callback; the
ordinary F1 timeline remains unchanged.

Any ambiguity after candidate intent retains the existing exact rollback path.
Rollback recovery does not reopen historical eligibility or Debian A/B inputs,
so loss of auxiliary evidence cannot preempt an already-authorized rollback.
`PROMOTED_CLOSED` is journaled before result publication; a publication fault
is repaired idempotently from the terminal record without rollback, candidate
replay, or another device transition.

## Host evidence

Read-only validation of the preserved V3406 `-03` evidence accepted all 20
journal records, the canonical approval, one candidate transfer, one rollback,
strict candidate health, strict final V2321 health, and same-target identity.

The existing A/B validator independently reopened both corrected private
images. Each was 2,147,483,648 bytes, both image hashes were equal to the
published Phase 2 display input hash, and the deterministic image and presenter
flags passed.

Focused regression passed `215/215`. It includes arbitrary-callback rejection,
fake prior-state/result/health rejection, different-target rejection,
auxiliary-free rollback recovery, strict first health, post-health guard loss,
promotion timeline isolation, promoted-closed rollback refusal, and terminal
result-publication fault repair. Python compilation and `git diff --check`
passed.

Independent H0 review returned `PASS / GO` with no unresolved Critical, High,
Medium, or Low finding. The reviewer separately ran Python compilation, 196
relevant tests, and `git diff --check`, all passing. The review touched no
device, USB endpoint, network, or S22+ execution path.

## Proportionality boundary

This unit stops here. It adds no daily D1 runner, no new observer framework, no
new transport, no candidate image, and no live manifest. Most new code is
eligibility validation and fault regression; live behavior remains one bounded
reboot/health tail over the existing F1 owner.

The next unit, if selected, is limited to fresh A90 connected read-only
preflight and a data-only final manifest. It still requires a separate fresh
approval before any live promotion.

## Keyed-input closure amendment

The first connected-preparation audit found that the runner treated the exact
clean A/B SHA256 as the final staged SHA256. That would accept a deterministic
base with no observer authorized key and make the later D1 SSH observation
unusable. No live manifest or authority existed, so no device transition was
affected.

The corrected gate validates the clean A/B receipt as the immutable base, then
requires a distinct 2 GiB keyed image whose materialization receipt already
passed the V3406 staging validator and remains in the bound-file closure. A
clean unkeyed image is now explicitly rejected. The current Phase 2C packet
bindings were refreshed to the exact current staging adapter and orchestrator.

Focused validation passed 98 tests and the actual 2 GiB clean-base audit.
Independent changed-closure review returned `PASS / GO`, independently passed
180 focused tests, and found no device-authority or flash-surface expansion.
