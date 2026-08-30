# S20+ autonomous public-health read-leaf coordinator H0 qualification

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0_AUTONOMOUS_PUBLIC_HEALTH_READ_LEAF_PASS_GO_NOT_ACTIVE**

## Objective

Define the narrow coordinator leaf that can serialize one future autonomous
public-health read against the exact initial attended session. It may model one
read lease, validate the already-qualified retained-evidence result, and model
one completion that always parks the campaign. It owns no connected command,
private writer, clock, executor, campaign opening, control action, or live
authority.

The qualified implementation and focused test are:

- `workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_coordinator_h0.py`;
- `tests/test_s20plus_g986n_autonomous_public_health_coordinator_h0.py`.

Exact reviewed identities after the mechanical status rotation are:

- read-leaf source: 53,200 bytes, SHA-256
  `e2952245bf4433044fae12ff8114ee9ff4239cbacd173a83cdc5a3dfcfa3d2c6`,
  activation-normalized SHA-256
  `314de4c38ff9a629b4350942100668155d69fd7f990014ac49df060d6a2907e0`;
- focused test: 31,160 bytes, SHA-256
  `2f322e064e9f120fc04f019f5244448814a30665698fab9ab3b30d5f74fc72ab`.

Independent exact-byte review returned `PASS_GO` for the permanently
commandless model. Focused validation passed 46/46 and the five autonomous H0
suites passed 140/140; `py_compile` and scoped `git diff --check` passed. This
qualifies no writer, activation, campaign, session, or device read.

## Frozen source closure

This unit must not edit or execute the qualified base coordinator as a module.
It pins these current exact files:

- base coordinator: 105,904 bytes, SHA-256
  `87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd`,
  normalized SHA-256
  `8d28f370f16d1f0d86eaa456fae09c01160d9fd8445529184643223934f4aea1`;
- evidence/accounting owner: 96,626 bytes, SHA-256
  `1f737347330b5a2ed1c85e51cca852309ba25e15e7a68d59f6bd6bb4961ba0c4`,
  normalized SHA-256
  `79d2fb339ce6c972790e28675ec407d2dbbd2f8e6f1b1e87008f332cbb708db1`.

The evidence owner transitively pins public health SHA-256
`03abc4fe5cbe258c0f8eafce27f1230960dc448af616a8f8a14b0e1809baaa4b`
and inventory SHA-256
`3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81`.
Any drift stops before a lease model. Editing the old coordinator would also
invalidate the evidence owner's closure, so this unit is a separate leaf.

After full and normalized hash verification, the H0 leaf may compile and
execute only the exact commandless evidence-owner source to reuse its selected
pure validators. The selected-callable `MappingProxy` is not an isolation or
provenance boundary: function globals remain inspectable. That reuse is
acceptable only inside this permanently commandless model and grants no live
writer/executor trust. A future live integration must bind and review its own
execution and provenance closure rather than infer it from API selection.

## Permanent dormant boundary

The only CLI is host-only `--render-plan`. The following gates remain false:

- coordinator active;
- live authority;
- mechanical activation;
- private-writer integration;
- public-health executor integration;
- trusted-clock provenance; and
- combined control integration.

Live entrypoints reject before caller input or filesystem access. The plan has
empty device-command, device-effect, root, reboot, Download, Odin, payload,
partition, R1, and F1 surfaces. A boolean change cannot create a writer or
executor and cannot activate this leaf.

The retained model spans three independently fixed private roots: the base
coordinator root `s20plus-g986n-autonomous-research`, the evidence root
`s20plus-g986n-autonomous-public-health-evidence`, and the read-leaf root
`s20plus-g986n-autonomous-public-health-read-leaf`. No caller chooses a root or
filename. This H0 has no filesystem reader/writer for those roots; the location
mapping and namespace rules are requirements for the future combined writer.

## Exact read-leaf state machine

Only these three states exist:

| State | Exact coordinator head | Only modeled successor |
|---|---|---|
| initial | exact initial `session-opening.json` bytes | ordinal-1 public-health lease |
| pending | exact lease bytes | exact parked completion after retained-evidence validation |
| parked | exact completion bytes | none |

Initial admission requires the exact attended guard/opening/session allocation,
healthy and unexpired `healthy-normal`, the current head byte-identical to the
session opening, target/build/source identity unchanged, and all control and
read/evidence counters zero. No baseline, reboot, Download, health, terminal,
prior lease, second session, or foreign node may exist. Cross-session carry and
ordinal greater than one are deliberately outside this model.

The leaf accepts the exact evidence-owner schemas without adding keys:

- `s20plus_g986n_autonomous_public_health_read_lease_v1`;
- `s20plus_g986n_autonomous_public_health_read_complete_v1`.

The lease models one atomic evidence debit in both child and campaign scopes:

```text
read_operations: 0 -> 1
private_evidence_bytes_reserved: 0 -> 524288
private_evidence_bytes_consumed: 0 -> 0
```

It binds the exact accounting opening, current context and head bytes, source
identity, prior zero hashes, fixed host-tool identity, both complete scopes,
and expiry. It requires `attempt_consumed=true`, `controls_blocked=true`,
`terminal_blocked=true`, `completion_required=true`, and
`replay_authorized=false`.

The evidence result is only a proposed settlement until its exact retained
bundle is re-derived and the coordinator completion is validated. Completion
must bind the exact lease and result hashes, use identical measured bytes in
both scopes, release the reservation once, and carry:

```text
completion_mode = permanent-h0-parked
controls_unblocked = false
terminal_unblocked = false
campaign_parked = true
replay_authorized = false
```

No terminal, guard removal, second lease, control, or F1-readiness successor
exists. A completion-output loss may only validate and re-emit the same model;
it never settles twice.

## Serialization boundary

The old coordinator uses action-specific final names. If a read and a control
writer could both publish different names against one predecessor, no-replace
alone would not prevent sibling successors; detecting them afterward would be
too late if either command had dispatched. This read leaf avoids that race only
by admitting no control action and by requiring the old coordinator to remain
dormant. They can never be parallel live dispatchers.

A later combined read/control coordinator needs one exclusive successor owner
or universal transition slot before any command dispatch. This leaf does not
claim that future property and cannot be reused as control integration.

## Complete byte accounting

The qualified evidence model reserves 524,288 bytes for the exact 19 evidence
files and proves their combined maximum is 507,904 bytes. That charge excludes
structural journal JSON, so this leaf adds a separate structural class rather
than silently treating excluded bytes as free.

Exactly eight retained structural final nodes are permitted, with canonical
bytes including the trailing newline bounded as follows:

| Root | Final node | Maximum bytes |
|---|---|---:|
| base | `active-campaign.json` | 8,192 |
| base session | `opening.json` | 4,096 |
| base session | `session-opening.json` | 4,096 |
| evidence session | `accounting-opening.json` | 16,384 |
| read leaf | `public-health-read-lease-000001.json` | 8,192 |
| evidence session | `read-intent-000001.json` | 4,096 |
| evidence session | `read-result-000001.json` | 8,192 |
| read leaf | `public-health-read-complete-000001.json` | 4,096 |

The exact eight-node aggregate must be at most 49,152 bytes. The same actual
aggregate is conservatively charged to both child and campaign structural
scope because this model has only one session and one read. Canonical 2026
host fixtures remain below the aggregate and every per-node cap. The aggregate
cap is lower than the 57,344-byte sum of the individual caps, so simultaneous
expansion is also bounded.

The original standalone current-context raw value is separately size- and
hash-bounded but has no final node or separate charge. Its exact canonical
semantic bytes are embedded in the retained lease and therefore count inside
that node's 8-KiB cap and the 48-KiB aggregate. At terminal validation there
are exactly eight structural JSON files and 19 evidence files, for 27 retained
regular final files across the three fixed roots. Directory and inode metadata are
filesystem-dependent; their grammar, count, ownership, mode, link, and
no-follow requirements are structural rather than byte charges.

This H0 model can validate raw lengths and names but has no writer. A future
writer must pin all three roots by directory descriptors, reject missing/extra/
indirect names, check size before reading, recompute canonical raw lengths,
check the projected per-node and 49,152-byte aggregate before publication,
publish atomic no-replace with file and directory fsync, then reopen and
recompute. Oversize or uncertain publication parks without cap expansion,
deletion, refund, or replay.

## Cross-root cuts and no replay

- No lease: no autonomous authority.
- Lease durable, mirror absent: the exact mirror alone may be completed with
  zero commands; the reservation and all blockers remain.
- Mirror plus incomplete raw/receipts: `uncertain-consumed`; park permanently,
  retain the reservation, and forbid replay, refund, control, or terminal.
- All six raw pairs and receipts complete: missing health/result may be derived
  only from those retained bytes with zero commands.
- Exact 19 files and result durable, completion absent: one exact parked
  completion may be modeled with zero commands, including after expiry,
  disconnect, or boot drift.
- Completion durable, CLI output lost: validate/re-emit only; no second
  settlement or successor.

A presence flag cannot prove settlement. Until exact completion bytes and the
full evidence ancestry validate, cut classification conservatively treats the
reservation as unresolved. Caller timestamps are numeric fixtures only; they
cannot prove durable order or same-invocation provenance and can never unpark.

## Threat boundary and recovery bytes

An independently authorized writer running under the same host UID could forge
files that owner/mode checks alone cannot authenticate. Such concurrent writers
are outside this proposed lane and must be excluded operationally or closed by
a separately reviewed single-writer/provenance mechanism before activation.

Rotating the coordinator, evidence parser, or recovery code while an unmatched
lease exists could orphan zero-command recovery. Live activation therefore
requires immutable versioned recovery bytes retained for the guard/lease, or a
mechanical rule that prevents source replacement until the lease is terminal.
This model proves neither mechanism.

## Future operator interaction

The operator prefers bounded nonpersistent, recovery-preserving research to
continue without repeated prompts. That is the future interaction objective,
not present standing authority. After the complete coordinator, writer,
executor, recovery, and evidence closure is independently reviewed and
mechanically activated, one new attended exact-target/current-boot opening may
authorize its finite campaign. This leaf still ends after one parked read.

Any permanent mutation, root-data write, partition payload, or risk of losing
the recovery path always stops and requires fresh attended consent under a
separately reviewed tier.

## Gates remaining

1. Implement the fixed private writer with trusted journal order, clock, and
   recovery-source retention; independently test every publication cut.
2. Implement the exact no-input six-command producer and bind its outputs to
   the lease before any command; review target isolation and no replay.
3. Review the combined closure, rotate the binding target contract, and
   mechanically activate only the public-health-only action surface.
4. Obtain one fresh attended exact-target/current-boot campaign opening after
   activation. Pre-activation requests cannot be banked.

## Work performed

This unit added the commandless read-leaf model and hostile tests and updated
the target contract, goal, and this report. It ran no ADB, USB, `su`, root,
device-network, reboot, Download, Odin, payload, partition, R1, F1, campaign,
or private live-evidence action. The only promotion is exact-byte `PASS_GO` for
this permanent H0 model; all live/writer/execution/mechanical gates remain
false, and no device state is claimed.
