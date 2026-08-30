# S20+ autonomous public-health evidence/accounting H0 qualification

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0_AUTONOMOUS_PUBLIC_HEALTH_EVIDENCE_PASS_GO_NOT_ACTIVE**

## Objective

Define the strict private-evidence, retained-return parser, and two-scope
accounting owner needed by dormant S20+ autonomous public health.
This unit owns neither connected command execution nor campaign creation. It
models how one complete fixed six-command read would be reserved, retained,
re-derived after a reporting cut, and charged to its existing child session
and attended campaign without replay.

The qualified pure-model implementation is
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_evidence_h0.py`.
It received exact-byte independent `PASS_GO` only for the dormant model. No
integration, activation, campaign, session, command, or device result is
claimed.

Exact reviewed identities:

- owner: 96,626 bytes, SHA-256
  `1f737347330b5a2ed1c85e51cca852309ba25e15e7a68d59f6bd6bb4961ba0c4`,
  activation-normalized SHA-256
  `79d2fb339ce6c972790e28675ec407d2dbbd2f8e6f1b1e87008f332cbb708db1`;
- focused test: 59,842 bytes, SHA-256
  `a65f52ab51d8a189725f817adc225a6a7202d0ed2f8a2d181e08dcd45b6860dd`;
- coordinator source: SHA-256
  `87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd`;
- public-health parser source: SHA-256
  `03abc4fe5cbe258c0f8eafce27f1230960dc448af616a8f8a14b0e1809baaa4b`;
  and
- inventory source: SHA-256
  `3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81`.

Focused validation passed 31/31; the four autonomous H0 suites passed 94/94.
`py_compile` and scoped `git diff --check` also passed. The post-status-rotation
review reconfirmed the exact identities above.

## Dormant boundary

All four independent gates begin and remain false:

- `EVIDENCE_ACTIVE = False`;
- `LIVE_AUTHORITY = False`;
- `MECHANICALLY_ACTIVATABLE = False`; and
- `COORDINATOR_INTEGRATED = False`.

The H0 CLI may expose only `--render-plan`. No single constant flip is enough
to reach a command, campaign mutation, or live evidence path. A future
consumer must require all four gates and exact reviewed source identities.
This owner is not mechanically activatable while the current coordinator lacks
the serializing read-lease and read-completion nodes defined below.

The evidence owner has exactly one standalone private root:

```text
workspace/private/runs/s20plus-g986n-autonomous-public-health-evidence/
```

It must not place evidence beneath the coordinator root, whose exact child set
is independently closed, and it accepts no caller root, path, run directory,
campaign/session ID, filename, serial, executable, command, callback, backend,
or output destination.

## Exact source and opening binding

Before modeling or consuming a read, the owner must reopen and bind the actual
bytes of:

- its own full and activation-normalized source;
- `s20plus_g986n_autonomous_research_coordinator_h0.py`; and
- `s20plus_g986n_autonomous_health_h0.py`, including that parser's exact
  inventory-source receipt.

Source substitution, import-cache substitution, size/hash drift, an
unreviewed activation-only normalization, or a changed transitive parser
binding stops before an accounting intent. The accepted identities are the
exact reviewed values recorded above; any drift returns this unit to H0 review.

The immutable coordinator guard and opening/session nodes are allocation-time
evidence, not current-state receipts. A future coordinator revision must first
validate its complete current chain and atomically publish one
`public-health-read-lease-N` as the sole successor of the actual canonical
head bytes. The lease binds the guard/opening/session hashes, exact current
head bytes and SHA-256, campaign/session and action ordinals, current
target/build/source boot and identity, issue/expiry times, healthy-normal
phase, absence of a pending effect or terminal, and both complete counter
scopes. The coordinator must revalidate that head immediately before
publication.

`accounting-opening` mirrors the allocation and exact current-head binding;
the evidence `read-intent-N` mirrors the already-published coordinator lease.
This owner cannot create the lease or mutate, renew, replace, or complete a
coordinator campaign/session. Missing, expired, terminal, foreign, guardless,
noncanonical, stale-head, one-scope, or identity-drifted state grants no
evidence intent. Because the present coordinator has no such lease, this H0
owner has no live or mechanical activation path.

## Dual-scope reservation and debit

The only accounting keys are:

- `read_operations`;
- `private_evidence_bytes_reserved`; and
- `private_evidence_bytes_consumed`.

The current coordinator counter schema contains none of these keys. A future
reviewed coordinator revision must add them to both child and campaign
snapshots and to every current-head transition; until that happens, this owner
only models and validates the proposed equations and cannot issue a lease.
The present pure model accepts only the initial attended session with zero
read/evidence counters. It rejects cross-session carry rather than accepting
unauthenticated predecessor hashes or caller-supplied campaign usage.

The standalone root contains only a direct `campaigns` directory. Campaign and
session directories are derived, never supplied, as
`campaign-<sha256(campaign_id)>/sessions/session-<sha256(session_id)>`; each
level accepts at most 256 direct closed-grammar directories and never deletes
history. A session contains only `accounting-opening.json`, paired
`read-intent-%06d.json` / `read-result-%06d.json` nodes, and matching
`read-%06d/` directories. Each read directory contains exactly six stdout
files, six stderr files, six receipt files, and `health.json`. The lease
ordinal is the evidence ordinal. This first pure model accepts only ordinal 1
in the initial attended public-health-only session, and the lease head must be
byte-identical to the exact session opening. Its completion is conservatively
parked. It admits no later lease, interleaved control, or cross-session carry.
A future coordinator revision must validate an exact successor head and the
complete chain segment before adding any of those transitions. Gaps,
duplicates, a second intent, stale campaign/session derivation, or an extra
node stop.

The future coordinator lease, not an evidence-only branch, atomically debits
one `public-health` read and reserves exactly 524,288 bytes in both child and
campaign scopes. For each scope, from the exact current predecessor:

```text
read_operations' = read_operations + 1
private_evidence_bytes_reserved' = private_evidence_bytes_reserved + 524288
private_evidence_bytes_consumed' = private_evidence_bytes_consumed
consumed' + reserved' <= scope_private_evidence_bytes_max
```

A child can reserve at most 64 reads within 32 MiB; a campaign can reserve at
most 256 reads within 128 MiB. The same read uses the same ordinal and charge
in both scopes; it does not receive two independent capacities.

The coordinator lease and mirrored evidence intent must contain both complete
post-debit snapshots and their actual predecessor hashes. A debit-only node,
one-scope update, relational counter
reset, bool-as-integer value, overflow, reservation beyond either limit, or
counter state not derived from the current opening/result chain grants no
command or next action.

On normal completion, the future coordinator completion node releases the
same reservation and applies the identical measured evidence size to both
scopes:

```text
read_operations'' = read_operations'
private_evidence_bytes_reserved'' = reserved' - 524288
private_evidence_bytes_consumed'' = consumed' + actual_evidence_bytes
consumed'' + reserved'' <= scope_private_evidence_bytes_max
```

For any validated snapshot, `completed_reads` equals `read_operations` when
reserved is zero and `read_operations - 1` when exactly one 524,288-byte
reservation is outstanding. It additionally requires
`consumed <= completed_reads * 507904`; arithmetic never replaces exact prior
result/completion ancestry.

`actual_evidence_bytes` is the exact sum of the published file lengths,
including each canonical JSON trailing newline: six stdout/stderr raw pairs
bounded to 393,216 bytes total, six receipts bounded to 8,192 bytes each
and 49,152 total, and one canonical health result bounded to 65,536 bytes.
Thus the maximum charge is 507,904 bytes, below the 524,288-byte reservation.
Filenames, directories, allocation metadata, accounting opening, intent,
evidence-set manifest, result, and coordinator nodes are excluded. Every
receipt and the derived health JSON is sized before publication; expansion
past its individual or aggregate bound parks the reserved read without
publishing an oversized final value or permitting replay.

## One-read durable chain

The only valid order is:

1. one `accounting-opening` bound to the exact coordinator allocation and
   first validated current head;
2. one coordinator-owned `public-health-read-lease-N` atomically succeeding
   the revalidated current head and containing the dual-scope debit/reservation;
3. one evidence `read-intent-N` mirroring that exact lease and following the
   prior evidence opening/result;
4. six fixed command returns, each as direct no-replace stdout and stderr raw
   bytes;
5. six matching canonical receipts in ordinal order;
6. one bounded canonical public-health result derived by the reviewed internal
   retained-return replay path;
7. one evidence read result binding the lease, intent, exact 19-file evidence
   set, health result, actual charge, and proposed post-consumption counters;
   and
8. one future coordinator-owned `public-health-read-complete-N` succeeding the
   lease, binding that result, and settling both scopes into a parked head.

Each command receipt is at most 8,192 canonical bytes and binds its ordinal,
the fixed argv-template hash, the exact actual canonical argv hash, timeout,
return code, stdout/stderr sizes and SHA-256 values, plus exact execution-time
`host_tool_before` and `host_tool_after` receipts. The two tool receipts and
their values must be typed-equal within each receipt and across all six
receipts; each tool receipt contains the canonical ADB path,
device/inode/mtime, size, and SHA-256. The actual argv for selected-target
commands uses only the serial derived from the retained initial inventory and
the exact fixed snapshot script; it is never caller-supplied. A later replay consumes this
stored execution provenance and never reads the current tool. Receipt one
binds the evidence-intent hash; every later receipt binds the exact preceding
receipt bytes/hash, and no next ordinal may publish before that predecessor.
The read result binds receipt six, `health.json`, and the exact sorted 19-file
name/size/hash manifest. Through its predecessor chain and raw hashes, receipt
six is the sole chained commitment to all 18 pre-health files. Each receipt
also carries the proposed publication ordinal/time fields. This pure model
checks only their numeric monotonicity and that receipt six precedes a modeled
expiry/drift cut. It does not prove durable chronology or trusted time; a
future writer/coordinator integration must derive those facts from its own
no-replace journal order and clock rather than caller integers. Each raw pair
has a 64 KiB combined-output ceiling. The transcript remains exactly ADB version,
global inventory, selected `get-devpath`, two identical fixed public snapshots,
and final global inventory. This evidence owner records returns but owns no
subprocess or transport that can produce them.

The owner must never import, execute, or expose the command-capable inventory,
health, or coordinator module objects; in particular it never calls
`observe_once()`, `collect()`, `bounded_command()`, or `subprocess`. It reads
and hashes their source bytes only. A new locally frozen pure retained-return
parser accepts only the six expected template and actual argv encodings, ordinals,
timeouts, output bounds, raw tuples, and stored typed-equal tool receipts.
Host tests cross-check its semantic result against reviewed reference fixtures.
No function globals expose a command backend, and no caller callback/backend
or current ADB/tool access is reachable from this path.
The parser-derived health result must independently re-establish the exact
target/build, hashed serial/topology/boot identity, stable healthy Android,
SELinux `Enforcing`, shell identity, six-command accounting, and all existing
zero-write/root/reboot/mode-transition/payload/partition/other-target fields.
Its derived serial, topology, and boot hashes must be typed-equal to the
coordinator lease's current source identity; another same-model device, port,
or boot cannot settle the lease.
Stored semantic JSON without the complete bound raw return/receipt set is not
evidence.

All directories and direct regular files require fixed ownership and modes,
dirfd-relative no-follow access, bounded strict duplicate-key-rejecting JSON,
atomic no-replace publication, file fsync, and directory fsync. Raw return
files are mode `0400`; hardlinks, symlinks, special nodes, extra names, parent
replacement, ownership/mode drift, and source or raw-hash drift stop.
These are requirements for a future private-filesystem writer, not claims of
this pure model. The model validates the closed relative namespace only and
reports `private_filesystem_writer=false`; its test harness does not prove
real-root ancestor ownership, publication durability, or no-follow behavior.

## Reporting cuts and no replay

Once the coordinator lease exists, the read operation and 512 KiB reservation are
consumed for scheduling purposes. Intent-only and partial raw/receipt
publication cuts are `uncertain-consumed`: retain the reservation, park the
session, forbid command replay, forbid refund, and forbid any next read or
control action.

If and only if all six raw return pairs and their exact receipts are complete,
a later invocation may revalidate the immutable intent-time guard/opening/
session/head/lease bytes and frozen sources and derive a missing health result
or read result with zero command execution. It does not require current device,
boot, USB, or ADB state and never refreshes the lease. A published
health result cannot repair missing raw evidence. An existing complete read
result may be revalidated and re-emitted without a command; it cannot advance
the counters twice.

The cross-root publication cuts are exact. If the coordinator lease is durable
but its evidence mirror is absent, the owner may publish only that byte-bound
mirror with zero device command; the unmatched lease continues to block every
action. If the evidence read result is durable but coordinator completion is
absent, a future coordinator finalizer may validate that exact result and
publish exactly one parked completion node, including after expiry, with zero
device command. Every completion modeled here remains parked. Proving an
unforgeable uninterrupted same-invocation completion that can unblock a later
read is deferred to a future coordinator and execution-integration revision.
If coordinator completion is durable but CLI output was lost, a later call may
only revalidate and re-emit it; counters are never settled a second time.

A lease published before expiry remains valid after expiry, disconnect, or
boot drift only for this zero-command reporting path when all six returns and
receipts are complete. Completion then leaves the campaign expired/parked and
grants no new read or control. With missing return/receipt evidence, the lease
remains unresolved and parked; neither expiry nor reconnect permits replay.

An output-parser, evidence-publication, accounting, or CLI-reporting failure
never permits repeating a connected command. Uncertainty remains visible and
preserves the guard and reservation for reviewed recovery or attended closure.

## Separation from execution and higher-risk work

This owner contains no ADB executable, subprocess call, execution backend,
callback, observer transport, USB, root/`su`, reboot, Download entry/return,
Odin, payload, partition, R1, or F1 surface. Before execution integration, a
separately reviewed coordinator revision must own the read-lease/completion
nodes and require every read, reboot, Download, recovery, and terminal path to
validate the same current head and refuse an unmatched lease. This is the
bidirectional serialization boundary; an evidence-root flag alone can never
activate it. A later execution integration must construct the fixed
six-command producer internally, accept no caller command or backend, and
publish each actual return only after both the coordinator lease and mirrored
evidence intent are durable.

Control actions remain outside this unit. The separately active attended
root-health D0 remains per-invocation and does not enter an autonomous
campaign. R1/F1 approvals, journals, effects, or results never transfer into
this evidence lane. S22+ and A90 identities, evidence, counters, commands, and
authority remain zero and isolated.

## Future interaction model

The operator's direction is to avoid repeated per-action prompts for bounded,
nonpersistent work that preserves the recovery path. After the complete
coordinator, evidence, execution, cut-recovery, and control closure receives
independent review and is mechanically activated, one fresh attended opening
may bind the exact S20+ target, current boot, recovery conditions, finite
campaign limits, and allowlisted actions. Within that still-valid campaign,
an allowlisted public-health read need not request separate approval for every
ordinal.

This is a future interaction design, not current standing authority. The
opening must occur after activation and cannot bank the request that initiated
this H0 work. Target/build/boot drift, expiry, unhealthy Android, ambiguity,
lost recovery, or an unresolved cut parks or ends the campaign. Any permanent
mutation, new root-data effect, partition payload, or action that can weaken or
remove the recovery path always stops and requires fresh attended consent
under its separately reviewed tier.

## Gates remaining

1. Separately revise/review the coordinator-owned lease/completion chain and
   all control/terminal blockers, then implement/review the no-input
   six-command execution integration and campaign lifecycle/cut finalizers.
2. Implement and hostile-test the real private writer, including complete
   ancestor ownership, dirfd/no-follow access, no-replace durability, trusted
   journal ordering and clock provenance, and bounded recovery finalization.
3. Re-review the combined coordinator/evidence/writer/executor closure and
   mechanically set the four activation gates only if no finding remains.
4. Mechanically activate only after every required gate passes with no
   unresolved finding and obtain one new exact-target/boot attended campaign
   opening.

## Work performed in this unit

This unit added the exact pure-model owner and focused hostile tests and updated
`GOAL_S20PLUS.md` and this report. It ran no ADB, USB, `su`, device-network,
Odin, reboot, payload, partition, or live private-evidence command. The only
promotion is exact-byte `PASS_GO` for this permanently commandless H0 model;
all four activation gates remain false, and no campaign or device state is
claimed.
