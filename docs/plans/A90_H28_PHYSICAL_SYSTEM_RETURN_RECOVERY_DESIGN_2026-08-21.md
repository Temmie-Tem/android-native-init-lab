# A90 H28 physical System-return recovery design — 2026-08-21

## Disposition

H0 design only. This document grants no D0, D1, F1, reboot, ADB, flash,
physical-action, or guard-removal authority.

The fixed H28 F1 run `a90-h28-f1-20260821-01` has already consumed exactly one
candidate and one rollback attempt. Both exact boot images were written and
read back once. The final proved boot bytes are V2321, but the sole rollback
TWRP System-return request was uncertain and V2321 health is unproved. Neither
image nor either host TWRP request may be replayed.

## Objective

Close only this incident with one deliberately small capability:

1. bind the exact H28 manifest, nine-record terminal journal, active guard,
   consumed H28 candidate guard, and current independently reviewed recovery
   closure;
2. durably arm exactly one operator physical `TWRP -> Reboot -> System`
   continuation;
3. send no host ADB, TWRP, reboot, candidate, rollback, partition, or other
   device command;
4. after the operator confirms that physical action, perform one fresh
   read-only Native/ACM observation;
5. publish recovery closure only for exact healthy V2321, then remove only the
   capability-wide active guard; and
6. retain the H28 candidate guard permanently consumed.

This capability does not decide whether the original rollback System-return
request took effect. It proves only the later physical continuation and current
V2321 health. The original request remains unproved.

## Fixed interface

One fixed H28-only program accepts no manifest, run ID, path, device, serial,
command, image, outcome, or guard from the caller. It exposes three modes:

### Host launch trust boundary

The fixed launch is `/usr/bin/python3.14 -B -s -E` followed by the absolute
repository path to
`a90_h28_physical_system_return_reconcile_v1.py` and one fixed mode grammar.
The working directory is the repository root. The program rejects another
interpreter path, relative or symlinked source identity, enabled bytecode,
user-site or environment processing, a different working directory, ambient
local-module aliases, and unknown arguments before any host write or
instruction. A stdlib-only pre-import guard performs the interpreter, flag,
cwd, argv0, script, owner-path, and `sys.path` checks before importing the
owner; only then may the full module-identity guard and argument parser run.

The operator account, system Python installation, and absence of concurrent
same-UID hostile code are host trust roots, as they are for the already
qualified minimal F1 owner. Same-UID host compromise is not claimed to be
contained: it could directly forge the review, journal, guards, or terminal
independently of this program, so a sealed Python package would not close that
larger threat. Suspected host compromise is an immediate campaign stop. Within
the selected boundary, current-review validation, full execution-closure
rehash, fixed absolute paths, and the review lease reject ordinary source,
environment, alias, or pathname drift.

### `prepare`

Host-only. It verifies the immutable H28 manifest, exact nine journal records,
exact terminal, active guard, candidate guard, current review, and execution
closure. It performs no device discovery or action. It emits one approval token
derived from the fixed capability ID, run ID, manifest SHA-256, terminal
SHA-256, current review SHA-256, and current execution-closure SHA-256.

### `authorize --approval TOKEN`

Host-only. It repeats every fixed verification, accepts only the exact token
from `prepare`, and durably publishes an append-only sidecar
`10-physical-system-return-intent.json`. Only successful publication permits
the program to print the instruction for the attended operator to select the
exact A90 handset already showing TWRP and press `Reboot -> System` once.
The current independent-review bytes remain held by one no-follow descriptor
lease from the last pre-publication check through the post-publication
execution-closure recheck and instruction emission.

The program itself performs no device I/O. A missing, malformed, duplicate, or
changed intent parks. It never publishes or replaces a second intent.

### `finalize --operator-attended --physical-system-return-confirmed`

It requires the exact durable intent and repeats all immutable incident, guard,
review, and closure checks. It performs no recovery/ADB/TWRP command. Its only
device contact is the existing reviewed Native/ACM read-only observer, bounded
to exact V2321 health and the unchanged foreign-target disposition.

Immediately before creating that observer, it durably publishes exactly one
no-replace `20-native-observation-intent.json`, bound to the physical intent,
review, closure, manifest, and terminal. That record consumes the sole Native
observation whether the observer succeeds, fails, times out, or the host dies.
If it is already present while recovery closure is absent, every later
invocation parks without creating an observer.

On exact healthy V2321 it publishes the fixed incident
`41-recovery-closed.json`, preserving:

- `candidateReplay=false`;
- `rollbackReplay=false`;
- `originalTwrpReturnOutcome=UNPROVED`;
- `physicalSystemReturnConfirmed=true`;
- `hostRecoveryCommandCount=0`;
- `bootWriteCount=0`; and
- the observation-intent digest plus one canonical digest of the fresh V2321
  snapshot.

Only after that durable record exists may it remove the exact active guard.
It revalidates the current independent-review lease and the consumed candidate
guard before publication, before removal, and after removal. It never removes
the candidate guard. It also recomputes the execution closure before Native
observation, after observation, after recovery-record publication, and before
and after active-guard removal; drift parks without further action.

## Crash and replay rules

- Before intent: no physical continuation is authorized.
- After intent and before health: the physical action is consumed/unknown; do
  not publish another intent and do not instruct another press.
- After observation intent: Native observation failure, interruption, or
  non-V2321 health parks permanently with both guards and no second observer.
- Before recovery-record publication: remove no guard.
- After publication but before active-guard removal: park; do not reconstruct
  authority from a mutable observation.
- A later invocation may report completion only when the recovery record is
  exact, the active guard is already absent, and the candidate guard remains
  exact.
- No path permits candidate, rollback, TWRP, reboot, ADB, or physical-action
  replay.

## Required hostile tests

Reject changed/missing/extra journal records, wrong terminal or manifest,
missing/drifted guards, stale or changed review/closure, token substitution,
authorize twice, finalize without intent, finalize without both operator
flags, unhealthy/wrong resident, changed other-target disposition, any backend
effect method call, any attempted ADB/reboot/flash subprocess, publication
failure, guard loss before publication, active removal before publication,
candidate-guard removal, and a second physical instruction after intent.

## Review and activation

Implementation must receive one independent full H0 review of its complete
execution-critical closure and the corresponding target-contract exception.
A PASS qualifies only the capability bytes. A fresh explicit operator approval
is still required for the fixed physical continuation. Until both exist, the
current action is to keep TWRP open and press nothing.
