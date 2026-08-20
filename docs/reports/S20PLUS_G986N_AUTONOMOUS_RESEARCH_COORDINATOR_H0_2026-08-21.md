# S20+ bounded autonomous research coordinator H0

Date: 2026-08-21

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0 PASS_GO_NOT_ACTIVE**

## Scope and boundary

This unit implements a separate dormant H0 journal/state-machine candidate
required by the policy-only H0 owner.  It is not a mechanically activatable
live coordinator.  The implementation is
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_coordinator_h0.py`.
`COORDINATOR_ACTIVE=False`, `LIVE_AUTHORITY=False`,
`MECHANICALLY_ACTIVATABLE=False`, and `LIVE_ACTION_INTEGRATION=False`; the only
CLI is `--render-plan`, and there is no ADB, USB, Odin, shell, root, network,
device, observer, backend, or callback transport.  The policy owner remains
permanently render-only; no status or constant flip alone activates this
candidate.

The named H0 model contains only `public-health`, `reboot-system`,
`download-roundtrip`, and `prepare-f1-readiness`.  The last action is a
readiness terminal only.  It publishes no F1 intent or approval, sends no
Odin payload, and performs no partition transfer.  Root profiles remain
deferred design inputs.

## Reviewed implementation candidate

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_coordinator_h0.py` | 105,911 | `687dc5b64161dcd7a45c922ee67f9014e325543ea5951edf6cc3808cbf7d41d2` |
| `tests/test_s20plus_g986n_autonomous_research_coordinator_h0.py` | 53,108 | `06ce7b6147de077e3f646b3840731c073abebc09432573a0eeb01e4796ab0f16` |

The reviewed candidate coordinator normalized source identity was
`82c8f97f5ecae55e8f39be8a250a8929c511edf0cb7a15d9e591109164bacc75`.
It exact-loads and pins the current policy owner, D0 inventory, routine D0,
routine actions, and payload-free Download-exit source receipts.  Current
source bytes, canonical paths, regular-file identity, link count, size, and
hash are checked before a binding or journal state is accepted.
Download endpoint evidence accepts product `SM8250` only with the two pinned
paired-controller topology SHA-256 values from the reviewed S20+ helper;
all other topology hashes fail closed.

Independent exact-byte review returned `PASS_GO` with no unresolved H0
blocker after three blocker classes were reproduced and remediated: fixed-root
path/guard ownership, post-expiry node creation, and cached-context
backdating. The subsequent authority-neutral status/self-identity rotation
produced:

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_coordinator_h0.py` | 105,904 | `87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd` |
| `tests/test_s20plus_g986n_autonomous_research_coordinator_h0.py` | 53,050 | `a6655f3699f1f58861ff4d2313826f66798abcacd2f48d543e6a387b2e47749b` |

The post-review normalized coordinator identity is
`8d28f370f16d1f0d86eaa456fae09c01160d9fd8445529184643223934f4aea1`.
All activation and live-integration flags remain false.

## Fixed guard and journal closure

The only runtime roots are the fixed private paths
`workspace/private/runs/s20plus-g986n-autonomous-research/active-campaign.json`
and
`workspace/private/runs/s20plus-g986n-autonomous-research/campaigns/`.
An offline `model_campaign_opening()` creates one fresh internally generated
campaign/session identity and one 24-hour allocation model.  The effect-facing
`Coordinator` methods gate before input parsing or filesystem mutation and
remain unavailable because live action integration is absent; there is no live
campaign-opening CLI.

Final JSON names are written only with an unnamed `O_TMPFILE`, complete
write, file `fsync`, atomic no-replace `linkat(AT_EMPTY_PATH)`, and directory
`fsync`.  Reads use fixed-root component-by-component `O_NOFOLLOW`, fstat
identity checks before/after bounded reads, one direct regular link, and mode
`0400`.  Duplicate keys, non-finite values, bool/integer substitution,
non-canonical encodings, symlinks, hardlinks, special nodes, oversized data,
unknown/partial names, and replacement publication fail closed.

The canonical chain is:

`opening -> session -> baseline-N -> entry-N -> arrival-N -> return-N -> return-health-N`

The host-only opening publisher first claims one immutable
`phase=allocation-claimed` guard containing the exact canonical opening and
session values, their digests, current binding, source, campaign, and session.
Only then are the exact opening/session nodes completed no-clobber.  A write,
link, fsync, or close cut after the guard leaves that guard in place; recovery
completes only missing bytes that match the guard.  Guardless opening files,
foreign 0400 files, and partial/mismatched nodes are never generically
deleted, and a concurrent opening fails under the no-replace guard.  Every entry and return intent contains
both child and campaign post-debit counter snapshots in the same immutable
node.  Every Download roundtrip first publishes an exact baseline node for
the next ordinal.  That node proves endpoint count zero, the fixed empty
listing SHA-256 and grammar, and the current source/campaign/session/
predecessor.  Entry-N must immediately follow that exact baseline and bind
its actual predecessor hash; baseline-only, stale, reused, missing, forged,
or nonempty baseline states grant no effect or recovery.  A Download entry
consumes one transaction, consumes one component
effect, and reserves its return effect before the entry intent.  Return
converts that reservation without new capacity.  Reboot is rejected while a
return is reserved.  Counters are validated relationally and monotonically;
the roundtrip ordinal must equal the current campaign roundtrip count.

The validator follows actual predecessor bytes, not caller-supplied strings.
It derives campaign/session, source identity, ordinal, endpoint, and current
predecessor from the fixed current guard and validated nodes.  Arrival is the
only node that binds an endpoint; return derives and rechecks that endpoint
from the validated arrival.  Old ordinals, foreign source or endpoint values,
actual predecessor mismatches, debit-only/single-scope nodes, unreachable
nodes, and extra namespace entries grant no authority.

Every post-session node carries a strict integer `issued_at`.  The validator
derives `current_time` from `validate_chain(now=...)`, requires nondecreasing
chain timestamps, rejects future timestamps, and requires every new baseline,
entry, reboot, and readiness terminal to be issued no later than both session
and campaign expiry.  Baseline and entry may share one validated timestamp.
After expiry, only an already pre-expiry entry may continue through bound
arrival and payload-free return, and only the resulting return health may close;
an already pre-expiry reboot may receive only its required health observation.
No post-expiry node can create a new transaction, baseline, entry, reboot, or
terminal.

Each model builder rechecks the actual host clock internally and rejects cached
or backdated contexts whose bound fields no longer match a fresh chain.  The
baseline/entry pair captures one trusted timestamp once and uses it for both
nodes.  The H0 model therefore rejects cached-context backdating; any future
live integration must repeat the clock/chain check immediately before atomic
final publication because that is a future-gate boundary.

Every reboot and payload-free return intent is followed by a strict canonical
healthy-Android observation node.  The observation binds the exact target,
serial, topology, and a new boot ID that is not reused anywhere in the chain.
Until that node arrives, the phase is respectively
`reboot-health-pending` or `return-health-pending` and no next control or
readiness terminal is allowed.  Expiry recovery is read-only and exists only
for the current reserved return or pending health observation.  Arrival phase
permits only the bound payload-free return; return-intent phase permits only
bound health observation/final-health.  It cannot
open a new baseline, entry, transaction, or capacity.  A resolved return has
no recovery authority.  Terminal validation stops at
`READY_FOR_ATTENDED_F1` only from healthy normal Android with zero F1 intent, approval consumption, Odin
payload, or partition transfer.  If a reporting cut loses the guard after a
terminal is present, the terminal-cut classifier exposes only a no-authority,
no-device-command receipt; it never reactivates the campaign.

## Hostile coverage

The focused suite covers dormant direct-helper zero-call behavior, caller
request/path/callback rejection, exact source binding, strict target identity,
duplicate/noncanonical/nonfinite JSON, bool/integer rejection,
O_NOFOLLOW/fstat bounded reads, exact closed path grammar, traversal,
intermediate-ancestor symlink, parent-swap, dirfd-relative unlink-swap,
symlink/hardlink/extra/partial nodes, atomic no-replace publication, immutable
guard-first concurrent opening, guardless foreign retention, modeled
write/fsync/link/close cuts after the guard and between nodes, old ordinal,
foreign guard/source/endpoint, third-topology rejection, typed issued-at,
monotonic/future/expiry timestamps, exact-boundary rejection, pre-expiry
post-expiry continuation, cached-context backdating, and hostile post-expiry
persisted nodes, nonempty/stale/
reused/missing/forged baseline, entry-without-baseline, actual predecessor mismatch, both-scope
counter publication, max-edge return reservation, unresolved-entry reboot
blocking, expiry-before-arrival/return, terminal cuts, and the pre-F1 zero
payload boundary.  Journal final uid/gid continuity is checked against the
validated private parent; no direct unlink/rmdir helper surface remains.

The host-only focused suite is **53/53**.  No private run, campaign, guard,
device command, reboot, USB transition, Odin invocation, root action,
network request, or live evidence was created by this unit.

## Remaining gates

This is an H0 journal/state-machine candidate, not live authority.  Before any
activation consideration, a separate exact live-action integration must add
and bind the empty Download listing producer, routine-D0 health observer,
read/evidence counters and durable receipts, fixed reboot/return backend,
child-session lifecycle, and all reporting-cut recovery paths.  Those pieces
plus the exact source/test/report identities, hostile cuts, execution-critical
helper closure, this permanent attendance-boundary change, and independent
safety review are mandatory before activation.  A later activation must
change coordinator and target-contract status together, preserve the policy
owner's render-only property, and still require a fresh attended campaign
opening.  F1 and R1 remain freshly attended.
