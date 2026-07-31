# A90 Resident Boot Promotion v1

Status: `H0_RUNNER_REVIEWED_NO_LIVE_MANIFEST`

This is a target-specific F1 extension for the A90 only. It defines how one
previously exercised native-init candidate may become a known-healthy resident
experimental baseline without immediately flashing the rollback image. It does
not grant live authority, create a final manifest or approval, or apply to
S22+.

## Purpose

Ordinary Process v2 remains the default: one boot-only candidate attempt,
bounded observation, mandatory exact rollback, and verified final health. That
is appropriate for a new experiment but makes every repeated Debian handoff
pay the Download, candidate, and rollback cost again.

F1-RP v1 is a one-time adoption transaction. It installs one exact,
previously exercised A90 native-init boot, proves it twice across a separate
resident reboot, and either closes it as the resident baseline or performs the
exact rollback already authorized by the original approval.

## Scope

The extension preserves every permanent boundary in `AGENTS.md`:

- one explicitly identified, operator-owned and attended A90;
- only the `boot` partition may receive a partition payload;
- the checked A90 transport remains `native_init_flash.py`;
- one exact V2321 rollback is present, readable, hash-verified, and physically
  recoverable before approval;
- no raw `dd`, fastboot, non-boot partition, format, security-state change, or
  target transfer is allowed; and
- no evidence or authority transfers to S22+ or another A90.

The transaction may use the already-reviewed A90 absent-only SD rootfs staging
path before candidate intent. It introduces no new staging destination,
transport primitive, generic deletion, or delete-and-restage repair. The
immutable rootfs source must be published under its exact final path and
SHA256, and the fixed handoff work path must be absent. Fresh preflight
classifies the final source as exactly one of `absent` or `exact`. Any other or
ambiguous disposition stops before approval.

## Candidate Eligibility

F1-RP is not a shortcut for an untested candidate. Before the promotion
manifest can be prepared, host evidence must bind:

- an earlier closed A90 F1 run of the exact candidate SHA256;
- exactly one candidate transfer and one rollback transfer in that run;
- no candidate or rollback replay;
- exact native version/build and `selftest fail=0` reached on the candidate;
- exact V2321 rollback and final health from the earlier run;
- current deterministic build and execution-critical source closure; and
- the corrected Debian A/B image and its host-only qualification receipt.

The earlier run may be formally no-proof for a later observation boundary. It
must still contain affirmative candidate boot-health evidence. Missing or
ambiguous candidate health makes the image ineligible.

The validator reopens the prior manifest, prepared approval, complete
contiguous journal, result, and canonical timeline. It parses exactly one raw
candidate version line and one exact selftest line, and repeats that strict
parse for the final V2321 baseline. Summary booleans alone are insufficient.
It reconstructs the prior canonical Process-v2 approval binding and requires
the same A90 bridge and recovery identity as the promotion target; evidence
from another target cannot qualify the candidate.
The raw corrected Debian A/B build receipt is delegated to the existing exact
2 GiB qualification validator; that helper's path, size, and SHA256 are also
manifest-bound.

The A/B images are deterministic clean bases and intentionally contain no
observer authorized key. They are never the final staged resident input. The
final input must be a new-inode per-run keyed child whose materialization
receipt is accepted by the V3406 staging validator and retained in the bound
execution closure. The keyed image keeps the exact 2 GiB size but must not have
the clean A/B SHA256.

## Immutable Manifest and Approval

The future data-only manifest must select `mode=a90-resident-promotion-v1` and
use schema `a90_native_init_f1_resident_promotion_v1`. That schema is accepted
only for a V3406 run containing an explicit resident-promotion object; ordinary
V3406 display manifests keep their existing attended display schema. The
promotion manifest must bind at least:

- exact target profile and fresh connected target-evidence digest;
- candidate path, size, SHA256, version, and build;
- rollback path, size, SHA256, version, and build;
- prior closed-run evidence and its digest;
- corrected keyed rootfs input path, size, SHA256, expected final SD path,
  expected final size and SHA256, and fresh final-source disposition
  (`absent` or `exact`);
- exact work path and its required fresh-preflight absence;
- runner, Debian A/B qualification helper, checked flash helper, staging
  adapter, bridge, observer, and ModemManager-guard SHA256 values;
- candidate and resident health predicates;
- one resident reboot command and timeout; and
- physical Download recovery evidence.

One fresh F1-RP approval binds that complete manifest and authorizes at most
one absent-only rootfs staging attempt, one candidate attempt, one resident
reboot, and the necessary exact rollback. The staging write is authorized only
when the bound fresh-preflight disposition is `absent`. A source already
classified `exact` takes a read-only verified-existing path with zero staging
attempts. Once the candidate attempt begins, rollback must never wait for a
second acknowledgement. The approval cannot be reused after a closed outcome.
After `PROMOTED_CLOSED`, `ROLLED_BACK_CLOSED`, `ABORTED`, or `BLOCKED`, any
later staging or candidate attempt requires a fresh preflight, new journal, and
fresh approval.

`RECOVERY_REQUIRED` does not reactivate candidate, staging, or reboot
authority. The original durable transaction retains only the exact rollback
recovery authority needed to reach `ROLLED_BACK_CLOSED`; it may not select a
different artifact or repeat the candidate.

## Durable State Machine

```text
PREFLIGHT
-> APPROVED
   | rootfs=absent -> ROOTFS_STAGE_INTENT -> ROOTFS_STAGED
   | rootfs=exact  -> ROOTFS_EXISTING_VERIFIED
-> ROOTFS_READY
-> CANDIDATE_INTENT
-> CANDIDATE_ATTEMPT_STARTED
-> CANDIDATE_FLASHED
-> CANDIDATE_HEALTH_VERIFIED
-> RESIDENT_REBOOT_INTENT
-> RESIDENT_REBOOTED
-> RESIDENT_HEALTH_VERIFIED
-> PROMOTED_CLOSED
```

The journal records `ROOTFS_STAGE_INTENT` before the first staging write. That
state is unreachable when fresh preflight classified the source `exact`; the
runner instead reopens and verifies the existing regular file's exact size and
SHA256 without writing, then records `ROOTFS_EXISTING_VERIFIED`. Both branches
must reach `ROOTFS_READY`, with the work path still absent, before candidate
intent.

A staging failure may close `ABORTED` only after reopening device evidence and
proving the final source is either absent or exact and the work path is absent.
An exact final source is reusable only through a later fresh transaction's
read-only verified-existing branch; it is not deleted or restaged. Any
ambiguous staging result stops `BLOCKED` before candidate intent.

Before `CANDIDATE_ATTEMPT_STARTED`, a proven host rejection or local transport
parse failure may also close `ABORTED` without rollback. An ambiguous transport
result is not a proven pre-session failure.

From `CANDIDATE_ATTEMPT_STARTED` onward, every failure or ambiguity branches
only to:

```text
ROLLBACK_INTENT
-> ROLLBACK_FLASHED
-> ROLLBACK_HEALTH_VERIFIED
-> ROLLED_BACK_CLOSED
```

A rollback failure stops at `RECOVERY_REQUIRED`; it never retries the
candidate, substitutes an artifact, or invents another recovery path. Durable
completion evidence is reopened before any resume, and a completed candidate
or rollback transfer is never retransmitted.

After candidate intent, recovery depends only on the current immutable
manifest, approval, artifacts, and durable transaction journal. It does not
reopen the historical eligibility run or Debian A/B qualification input, so a
missing auxiliary receipt cannot preempt the already-authorized exact
rollback.

## Promotion Health Bar

The first candidate boot and the separate resident reboot must independently
prove all of the following on exact, distinct USB generations. The second
generation must be observed after the durable reboot intent and must differ
from the first rather than accepting a retained endpoint:

- exact candidate version and build;
- `selftest fail=0` and the manifest-bound health predicates;
- clean pstore at the required boundary;
- stable ACM and NCM identity on the named A90;
- the exact staged rootfs source SHA256; and
- absent `d3-handoff-work.img`.

The A90-only ModemManager exclusion is revalidated after every command in the
second health set and again immediately before durable resident-health intent.
Guard loss cannot close promotion.

No Debian handoff occurs in the promotion transaction. The corrected Debian
display image is exercised later by the ordinary resident D1 path. This keeps
the one-time installation decision separate from the first application-level
experiment.

## Terminal Results

`PASS_A90_F1_RP_RESIDENT_PROMOTED` requires zero or one rootfs staging attempts
as selected by the bound `exact` or `absent` disposition, exactly one candidate
attempt, one candidate transfer, two exact candidate health closures, one
resident reboot, zero rollback attempts, and `PROMOTED_CLOSED`.

`NO_PROOF_A90_F1_RP_CANDIDATE_ROLLED_BACK` requires one exact rollback and
verified V2321 health after any post-attempt failure. It does not promote the
candidate.

`RECOVERY_REQUIRED` is never PASS. A later recovery may use only the exact
rollback under the original durable transaction rules; it never repeats the
candidate.

`ABORTED` and `BLOCKED` are closed no-promotion results. Neither retains an
approval or permits a candidate attempt.

After `PROMOTED_CLOSED`, the consumed approval grants no standing future
recovery authority. The promoted candidate is the new known-healthy
experimental resident. A later fault uses a fresh, separately selected
recovery action.

## Evidence and Timeline

The append-only journal records every state and transfer boundary. The compact
successful timeline is:

```text
live_session_start
candidate_flash_start
candidate_flash_done
candidate_boot_ready
resident_reboot_start
resident_reboot_ready
promotion_health_verified
live_session_end
```

A rollback result uses the ordinary canonical rollback events. Rootfs staging,
intent records, exact hashes, USB generations, and health details remain in
the private structured evidence rather than expanding the public timeline.
Promotion-only events are accepted only when the caller explicitly selects the
manifest-bound promotion mode; ordinary F1 timelines cannot acquire them.
`PROMOTED_CLOSED` is journaled before `result.json` publication. A publication
fault is repaired idempotently from that exact terminal record and never turns
into a rollback or repeated candidate transition.

This policy change requires one independent review of the policy, state model,
manifest validator, and live execution closure. Repeated resident D1 runs with
unchanged machinery do not require another review ladder.

## Current Activation Boundary

The pure model
`workspace/public/src/scripts/server-distro/a90_resident_promotion_v1_model.py`
still has no device, transport, flash, approval, or execute mode. The separate
runner `workspace/public/src/scripts/server-distro/a90_resident_promotion_v1.py`
reuses the reviewed V3403 staging, candidate-transfer, journal, and rollback
owner. Its only new live behavior is the manifest-bound resident reboot and
second exact health closure. It parses the bound prior journal rather than
trusting a summary receipt.

Independent H0 review closed PASS with no unresolved finding. No fresh
connected preflight, final manifest, prepared approval, or live authority
exists. Exact V2321 therefore remains resident and this policy is
non-executable.
