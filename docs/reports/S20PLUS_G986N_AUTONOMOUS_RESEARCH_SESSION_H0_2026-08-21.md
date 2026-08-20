# S20+ bounded autonomous research session H0

Date: 2026-08-21

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **PASS_GO - POLICY H0 ONLY - NOT ACTIVE**

## Objective

Reduce repeated operator gating for research that cannot write a partition or
persistently modify Android. After exact target selection, the proposed lane
may initially perform bounded public reads, normal reboots, and reviewed
payload-free Download round trips. Root surveys are a deferred later unit. It
stops in healthy
normal Android at `READY_FOR_ATTENDED_F1`; candidate/rollback transfer, F1
intent, approval consumption, R1 mutation, and partition access remain outside
the lane.

This is a permanent common-boundary proposal because the existing common rule
permits unattended device effects only for the A90 resident D1 exception. The
proposal is S20+-specific and requires independent safety review before any
mechanical activation.

## H0 owner

The policy owner is
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_h0.py`.
It exact-pins the current S20+ inventory, routine D0, routine-action, and
payload-free Download-exit sources. Its only CLI is `--render-plan`.
`RESEARCH_ACTIVE=false`, `live_authority=false`, and the rendered device,
root, effect, and partition-transfer lists are empty. It is permanently
render-only; a future live coordinator is a separate reviewed source and cannot
be activated by flipping this owner's constant.

Frozen H0 review candidate:

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_h0.py` | 14,605 | `64bd8ec99730f37e790cca1ca8e2ab1ea48377f5bdb08596ef23c58fe7daa2b7` |
| `tests/test_s20plus_g986n_autonomous_research_h0.py` | 15,987 | `7efa514b1d7c4dc223284397682bd55add0d57aeea1019bfb5cd804393b78378` |

The focused hostile suite passes 15/15. Together with the common Process-v2
documentation tests, the scoped total is 40/40 because this proposal changes
the permanent attendance boundary.

The frozen model accepts only these named future actions:

- `public-health`;
- `reboot-system`;
- `download-roundtrip`; and
- `prepare-f1-readiness`.

The five root profile names and fixed path/node-type design inputs are retained
only under `deferred_root_profiles`; none is present in the action list.

No request accepts a path, shell fragment, executable, property, service,
mount, credential, or output destination. The policy owner is permanently
render-only and contains no dispatch function or backend callback.

## Session and privacy bounds

A future active campaign requires one fresh attended opening and one durable
24-hour allocation: 256 reads, 128 MiB private evidence, 64 control
transactions, and 96 component effects. It permits at most 32 normal reboots
and 32 Download roundtrips. A reboot is one transaction/effect; a roundtrip is
one transaction whose entry debit also reserves the mandatory return effect
before entry intent. Return intent converts the reservation without new
capacity. It cannot renew or reset itself. Each child session
binds exact target/build plus hashed serial, topology, and current boot ID from
healthy normal Android, is at most four hours, 64 reads, 32 MiB, 16
transactions, and 24 effects, and debits the campaign monotonically.
A valid unmatched entry/reserved return survives child or campaign expiry only
to observe the bound arrival, send the exact payload-free return, and perform
final health. It opens no new baseline, entry, transaction, or capacity;
ambiguity retains the guard and requires attended recovery.
Each entry/return intent is the same strict canonical atomic no-replace node as
its child and campaign post-debit counter snapshots. Debit-only, partial-scope,
or malformed nodes grant nothing. Recovery nodes bind campaign/session,
roundtrip ordinal, source, endpoint where observed, policy identity, and exact
predecessor hash.

Root profiles are now deferred design inputs, not actions. A later unit must
bind the root launcher/transport, timeouts, input-size ceilings, stable
no-follow before/after receipts, directory count/name grammar, exact parser
sources, and hostile cut/replacement tests. This policy owner performs no root
read and extracts no file bytes.

Disconnect, unowned boot change, target/build/topology/source drift, unhealthy
Android, an unresolved foreign guard, ambiguous endpoint, budget exhaustion,
or uncertain mode transition expires or parks the session. An effect intent is
durable before the one control effect; an uncertain result never replays. The
future atomic roundtrip records an empty baseline before its entry intent,
binds the sole arrival, and may then issue only
`/usr/bin/odin4 --reboot -d <bound-endpoint>` with no payload. It does not reuse
or bypass the attended disconnect/arm/reconnect helper.

## Explicit exclusions

The proposed lane grants no Odin payload/archive/partition transfer, candidate or rollback transfer,
partition access, package operation, shared-storage write, root file write,
Magisk/module/configuration mutation, mount, delete, chmod/chown, `setprop`,
service control, SELinux change, generic `su`, caller command, S22+, or A90
authority. It cannot infer F1 or R1 from target health or readiness.

## Review and activation gates

Before activation the following remain mandatory:

1. freeze exact source and test identities;
2. validate the dormant owner and hostile schema/source/direct-helper cases;
3. independently review the common boundary change, S20 contract, runner,
   limits, privacy surface, and no-replay rules;
4. implement and separately review the live coordinator without bypassing the
   existing routine/download guards; and
5. mechanically activate only after the connected coordinator and all
   reporting-cut recovery paths pass review.

## First independent review

The first review returned `NO_GO` on five design blockers: contradictory Odin
wording, impossible reuse of the attended exit choreography, a caller-supplied
backend callback reachable after a constant flip, root profiles that mixed
regular files/symlinks/directories without exact commands or parsers, and
resettable per-session budgets.

The current rotation narrows the design. It permits no Odin payload but names
one fixed payload-free roundtrip return; replaces separate entry/exit with a
new atomic choreography; removes every dispatch/backend hook from the permanent
H0 owner; defers root actions until their full launcher/parser closure exists;
removes internal file-byte extraction; and adds a nonrenewable durable campaign
allocation whose transactions and component effects debit monotonic counters.
Fresh independent review is required.

The second review returned `NO_GO` because roundtrips were undercounted as one
effect, deferred Magisk hashing/enumeration still lacked input/time/parser
closure, and this report retained a stale backend-dispatch sentence. The
current rotation separately accounts each entry/return intent, removes every
root profile from the action surface, records the exact later closure gates,
and corrects the current-state wording.

The third review returned `NO_GO` because an entry at `effect_max-1` consumed
the last slot and made mandatory return impossible, and an unresolved entry
still allowed a normal reboot. The current counter model reserves return
capacity before entry, converts the reservation at return, and rejects every
non-return control while a roundtrip is unresolved. Child and campaign edge
fixtures cover both cut points.

The fourth review returned `NO_GO` because type-valid but relationally forged
counters could reset history, and expiry could revoke a reserved return and
strand Download. The current validator binds every transaction/entry/return/
reservation equation before and after debit. Expiry preserves only the exact
reserved arrival/return/final-health recovery sequence and grants no new
transaction or capacity.

The fifth review returned `NO_GO` because expiry recovery trusted an unbound
phase string and counter mutation was not explicitly atomic with both scope
snapshots and intent. The required future coordinator closure removes
phase-only authority and derives a canonical campaign/session/ordinal/source/
endpoint/predecessor chain from its fixed current guard and actual predecessor
bytes. Entry and return counter changes may exist only inside complete atomic
intent nodes; debit-only and partial-scope cuts grant no action.

The sixth review returned `NO_GO` because the policy owner's attempted recovery
validator still accepted caller-supplied expected identities and dictionaries,
allowing a self-consistent foreign/old chain. That validator is now deleted.
The permanently render-only owner grants no recovery transition; its binding
only enumerates the strict fixed-path canonical reader, current guard,
actual-predecessor, ordinal, child-membership, full-chain, and hostile fixtures
that a separately reviewed live coordinator must implement.

Fresh exact-byte review of the final dormant policy owner returned `PASS_GO`.
It confirmed that the owner exposes no dispatch, backend, recovery validator,
device/root/effect/transfer surface, or activation path; counters remain a pure
bounded model, roots remain deferred, and every live journal/current-chain duty
is explicitly reserved for a separate coordinator. The status rotation records
policy qualification only and creates no campaign, session, or device action.

Independent post-rotation review reconstructed the prior reviewed owner and
test bytes by reversing only the status/assertion strings and returned
`PASS_GO`. `RESEARCH_ACTIVE` and live authority remain false; no dispatch,
backend, recovery validator, command, root action, effect, or transfer surface
was added.

No device, ADB, USB, `su`, Odin, reboot, network, or private live evidence was
contacted by this H0 policy unit.
