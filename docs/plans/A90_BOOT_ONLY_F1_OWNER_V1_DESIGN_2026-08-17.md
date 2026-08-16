# A90 boot-only F1 owner v1 — structural design

Date: 2026-08-17
Target: operator-owned Samsung Galaxy A90 5G only
Tier of this document: H0 structural design
Device or live effect of this document: none
Status: **DRAFT — closes structure only. It implements nothing, qualifies
nothing, and grants no authority.**

This design exists to stop a loop, not to add a feature. Six independent
reviews of the per-candidate H27 runner each found real defects, and the
pattern was structural rather than accidental: every candidate got its own
~3,900-line runner, so every candidate required a fresh full review of safety
machinery that had nothing to do with the candidate.

The correction is one sentence: **review the code once, and make each candidate
data.**

## The loop being removed

Two mechanisms produced it.

**Self-reference.** The per-candidate runner stores review findings — reviewer,
date, incident class, validated invariants — as code constants. Filling them
after a review changes the source, which changes the execution closure, which
requires another review. The fifth review said so directly: filling the
bindings changes the closure, so re-freeze and re-review. There is no fixed
point.

**Lineage drag.** H27's runner inherited H24's, which inherited H18's. Booting
one kernel therefore re-validated rootfs staging, UFS inventory, Debian
handoff, display, SSH, and a seven-record H24 D1 journal. Reviews spent their
attention on machinery this experiment never executes, and the defects they
found were mostly in that inherited surface: an H18 predecessor left bound in
32 places, colliding journal namespaces, a `d1_runner_qualified` expectation
for a D1 runner that does not exist.

Both are removed by separating the reviewed artifact from the reviewed-about
artifact.

## The rule that breaks the cycle

**Review artifacts sign the owner closure. The owner closure never contains
review artifacts.**

A capability review signs a digest of the owner's source. That signature lives
outside the source, so producing it cannot change what it signed. The owner
carries no reviewer name, no review date, no incident class, and no invariant
list.

## Two review layers

| layer | when reviewed | changes with |
|---|---|---|
| owner capability | only when owner code changes | code |
| candidate manifest + hazard qualification | every candidate | data |

H28 (`CONFIG_ANDROID_BINDERFS=y`) and later candidates add a manifest and a
hazard qualification. They do not touch owner code, so they do not re-open the
owner capability review.

## The owner

`workspace/public/src/scripts/server-distro/a90_boot_only_f1_owner_v1.py`,
capability `A90_BOOT_ONLY_F1_OWNER_V1`.

It does exactly this and nothing else:

1. resolve exactly one A90 target, inventory attached devices, and report S22+
   and S20+ untouched;
2. fresh preflight: the actual resident version, build, and boot identity must
   equal the manifest's `expected_start`;
3. re-hash the candidate and rollback files **at execution time**, immediately
   before use;
4. require an empty durable journal and a fresh approval token;
5. `fsync` a `CANDIDATE_INTENT` record before any transfer;
6. transfer the candidate exactly once;
7. verify exact candidate version, build, self-test, and a bounded control
   response;
8. on failure, timeout, or ambiguity: roll back without retrying the candidate;
9. record the final health of whichever image is resident.

Removed relative to the per-candidate runners: rootfs staging, UFS inventory
and mount, Debian handoff, display, SSH, benchmark, observer, and every D1
path.

### Runtime rehash replaces delegated verification

The owner opens the private candidate and rollback files and hashes them itself,
immediately before use. That is the authoritative check.

This dissolves a problem that consumed two review rounds. Asking an independent
reviewer to verify private bytes contradicts the review contact contract, which
requires `workspace_private: 0`; delegating the check to tests then requires
binding a durable zero-skip receipt and the test source into the closure. Both
disappear when the executing owner does the hashing. No reviewer reads private
bytes, and no receipt needs binding, because the check happens where and when
it matters.

### Execution closure

Deliberately small:

- `a90_boot_only_f1_owner_v1.py`;
- a small shared module for canonical JSON and the append-only journal;
- the exact hash of the already-reviewed
  `workspace/public/src/scripts/revalidation/native_init_flash.py`, size 43,118,
  sha256 `366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53`;
- the manifest schema;
- the hostile state-machine tests.

**The owner must not import `a90_v3403_f1_orchestrator.py`.** That would pull
~7,900 lines back into the closure. The per-candidate runners are stdlib-only
today and the owner keeps that property; it is a closure constraint, not a
style preference.

## Manifest is data, never authority

The owner hardcodes, and the manifest cannot express:

- the `boot` partition as the only writable target;
- exactly one candidate attempt;
- exactly one rollback attempt;
- `--boot-block` and `--remote-image` at their defaults, so a caller-supplied
  path cannot widen the payload surface.

A manifest cannot name a command, a partition, or a retry count. It carries:

| field | for H27 |
|---|---|
| `expected_start` | H24 `0.11.192` + build + boot identity |
| `candidate` | path, size, sha256, expected H27 `0.11.194` version/build |
| `rollback` | path, size, sha256, expected V2321 identity |
| `flash_helper` | size and sha256 |
| `timeouts` | bounded |
| `hazards` | hazard IDs with their qualification digests |
| `owner_closure_sha256` | the reviewed owner it may run under |

### The manifest must match the device, not only a healthy device

Preflight proves two separate things, and conflating them is how the H18
predecessor survived 32 bindings in the H27 runner:

- the device is healthy;
- the device **is the resident this manifest expects**.

An H27 manifest presented against any resident other than H24 `0.11.192` stops
before any effect.

## Hazard binding

A boolean in data that nothing enforces is decoration. This session produced
that mistake twice — an empty invariant tuple that read as "nothing required",
and an `experiment_proof` field no consumer validated — so the hazard is bound
at three points:

1. a reviewed hazard-qualification artifact exists for
   `RKP_CFP_DISABLED_RESIDENT`, and the manifest binds it by digest;
2. the fresh approval token derives from a binding over the manifest SHA **and**
   the hazard ID, so approval cannot be given without the hazard in view;
3. the terminal records the same hazard ID with `accepted: true`, so what was
   accepted stays durable after the run.

An unknown or unqualified hazard ID stops the owner before any effect.

`RKP_CFP_DISABLED_RESIDENT` is the operator's 2026-08-17 decision to accept a
reduced kernel exploit-mitigation posture for as long as the self-built kernel
is resident, rather than proving the boot and returning to V2321.

## States

```text
PREPARED
  -> APPROVED
  -> CANDIDATE_INTENT
       -> PASS_A90_H27_RESIDENT_INSTALLED
       -> NO_PROOF_ROLLED_BACK
       -> RECOVERY_REQUIRED
```

- `PASS_A90_H27_RESIDENT_INSTALLED` — exact candidate identity and health
  verified.
- `NO_PROOF_ROLLED_BACK` — boot failure, timeout, observation failure, or
  ambiguity, followed by verified rollback health.
- `RECOVERY_REQUIRED` — rollback health could not be verified.

There is no `REFUTED`. Two review rounds went into its semantics and the
attribution receipt it would need, for a terminal this question does not
require. Cause analysis happens afterwards, as a separate H0 over the private
logs; an F1 terminal does not adjudicate why a kernel failed to boot.

## Retiring the per-candidate runners

Leaving them live would recreate the namespace collisions already seen. They
remain as historical recovery evidence and must not execute a new candidate:

```
a90_h15_ufs_f1_runner_v1.py   a90_h15_ufs_d1_runner_v1.py
a90_h16_ufs_f1_runner_v1.py   a90_h16_ufs_d1_runner_v1.py
a90_h17_ufs_f1_runner_v1.py   a90_h17_ufs_d1_runner_v1.py
a90_h18_ufs_f1_runner_v1.py   a90_h18_ufs_d1_runner_v1.py
a90_h24_ufs_f1_runner_v1.py   a90_h24_ufs_d1_runner_v1.py
a90_h27_ufs_f1_runner_v1.py
```

- a new manifest is consumable only by `A90_BOOT_ONLY_F1_OWNER_V1`;
- their approval prefixes (`A90-H15-F1-APPROVE:` … `A90-H27-F1-APPROVE:`) and
  journal namespaces (`h15-f1-live` … `h27-f1-live`) are forbidden to the owner;
- new run directories are keyed by owner version, manifest digest, and run ID,
  so no two runs can share a journal.

The H27 runner is retired before ever executing. Its candidate, builder version
`phase3-minimal-h27`, digests, and the kernel build behind them are unaffected
and carry forward.

## Hostile corpus

The owner is only as good as what it refuses. At minimum:

- manifest naming a non-`boot` partition, an extra partition, or a command;
- manifest asking for more than one candidate or rollback attempt;
- manifest presented against a resident other than `expected_start`;
- candidate or rollback whose runtime hash differs from the manifest;
- absent, symlinked, or non-regular candidate, rollback, or helper;
- flash helper whose hash differs from the pinned value;
- approval token that does not derive from this manifest SHA;
- approval token missing the hazard ID, or naming an unqualified hazard;
- reused or expired approval;
- non-empty journal at start;
- crash after `CANDIDATE_INTENT` and before result — must resume without
  candidate replay;
- candidate retry attempted after a failure;
- rollback attempted before candidate intent;
- terminal missing the hazard acceptance record;
- run directory colliding with a retired runner's namespace.

## What this design does not do

- It does not implement the owner.
- It does not qualify anything, and creates no approval, manifest, or hazard
  qualification.
- It does not authorize an F1. `GOAL_A90.md` still records that no successor
  candidate, transfer, or reboot is authorized.
- It does not claim the H27 candidate is correct; that stands or falls on its
  own build evidence.
- It does not remove the one-time cost. The owner needs a full capability
  review before first use. The saving is that H28 and later pay manifest and
  hazard review only.

## Sources

- `AGENTS.md`
- `docs/operations/targets/A90_TARGET_CONTRACT.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`
- `GOAL_A90.md`
- `docs/plans/A90_SELF_BUILT_KERNEL_F1_DESIGN_2026-08-16.md`
- `docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md`
- `workspace/public/src/scripts/revalidation/native_init_flash.py`

## Boundary

Produced host-only from repository documents. Device, `/dev`, USB, network,
S22+, and S20+ contacts are zero. No ordinal, identity, candidate,
qualification, approval, manifest, or command is created, and no D0, D1, or F1
authority is granted or implied.
