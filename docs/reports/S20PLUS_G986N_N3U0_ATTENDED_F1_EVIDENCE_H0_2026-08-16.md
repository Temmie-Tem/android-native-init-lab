# S20+ G986N N3-U0 attended F1 durable evidence owner H0

Date: 2026-08-16

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Status: **H0 PASS_GO - NOT ACTIVE**

## Scope

This bounded H0 unit implements a dormant durable owner for the future N3-U0
backend's private command stdout, stderr, and exact result receipts. It binds
the reviewed journal, concrete backend, and consumer-integration identities.
It neither changes those components nor exposes them as a connected runner.

`EVIDENCE_ACTIVE`, `active`, `live_authority`, `backend_exposed`, and
`integrated_live_consumer` are false. The only CLI is `--render-plan`; rendered
device-command and partition-transfer lists are empty. The binding S20+ target
contract still defines no N3-U0 F1 authority.

## Frozen candidate

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1_evidence_h0.py` | 23,833 | `730e5e78368894ef30e22d9e1f7d8356f6dfc00a536fc36b322ac0424cb84f09` |
| `tests/test_s20plus_n3u0_attended_f1_evidence_h0.py` | 15,605 | `384b1130a866893677c38ccc4c1678681471e8163b1ab649f199ca6e03595e94` |

The normalized owner SHA-256 is
`459c579cbefcb7916ccce7a00c595a772f3c0b23f679016a98be49ec85af9dbb`.
The deterministic binding is
`c59992f48361429812475b6535c4ad927ee63cad81f61a1d4e2ac59567402f47`.
It pins journal binding
`4695acca5c8d618eee7e16aaf665cbf66235a5a76aadc0a4322f490113cc2945`,
concrete-backend binding
`5561aabc35f20752702b8ef12ec6f8d4669bbef8b022ff5557c7925c34b9704b`,
and consumer-integration binding
`2a037eb3cab5f068b0d534d034fcadce51b26c3ee9f5874ec583b90905a6d6a6`.

## Evidence transaction

The owner revalidates its complete source/binding closure before every publish
or inspection. It accepts only a fixed journal run directly under the fixed private
N3-U0 runs root, one operation from a finite operation/predecessor map, and a
two-digit command ordinal. It revalidates the complete journal prefix and its
owning active guard, requires that operation's durable predecessor, and binds
the predecessor's canonical SHA-256 into the result.

Command arguments are not written in clear text; one canonical command hash is
stored. Private stdout and stderr remain only under the fixed private evidence
root. The owner atomically publishes:

1. `<operation>-<ordinal>.stdout`;
2. `<operation>-<ordinal>.stderr`; and
3. `<operation>-<ordinal>.result.json`.

Every direct evidence-directory, fsync, blob-write, blob-read, and namespace
helper repeats the dormant gate first and accepts only the fixed evidence root,
one direct lowercase run ID, and the finite filename grammar. Each final name
is created only after complete file bytes and file fsync via an
unnamed same-directory inode and no-replace `linkat`, followed by directory
fsync. Every file is a direct mode-0400 regular file with one link. The result
strictly binds run, distinct evidence-owner and journal bindings, operation,
ordinal, predecessor, command,
timeout, output limit, typed return code, and both raw size/SHA-256 receipts.

An intent with no evidence is `intent-consumed-evidence-absent`; stdout-only or
stdout-plus-stderr is `uncertain-consumed`. Neither permits replay. A result
without both earlier raw nodes, stderr without stdout, duplicate key,
bool/integer substitution, raw drift, indirect node, hardlink, unknown name,
or source drift stops as malformed.

## Hostile validation

The focused suite passes **18/18**. It covers dormant publication and
inspection before any write, unmocked exact render closure, complete raw/result
binding, duplicate publication/no replay, intent-only and both reachable raw
publication cuts, impossible publication orders, raw-byte drift, duplicate
JSON keys, bool/integer substitution, symlink/hardlink/unknown nodes,
atomic-link failure with no final name, wrong run root, missing predecessor,
and execution-source drift before publication and complete-evidence
certification, plus direct-helper dormant and `../`/foreign-root/arbitrary-name
rejection. Evidence directories and files must retain the fixed root's
owner/group identity; changing a run directory and every child together still
fails its root-to-run continuity check.

Independent review rejected three earlier candidates: publish/inspect did not
revalidate the evidence-owner binding, direct file helpers could bypass the
dormant gate and fixed root, and inspection checked file-to-run but not
root-to-run ownership continuity. The current exact candidate closes all three
with boundary-local validation and hostile fixtures. Fresh exact-byte review
returned `PASS_GO`; the status rotation changes no activation or live surface.

The 2026-08-20 raw-first transport rotation changed the exact backend binding,
so this owner now pins that reviewed candidate. Independent dependency-only
review returned `PASS_GO`; it remains inactive and non-integrated.

The later execution-integration rotation raises the exact raw bound to 8 MiB,
adds one gated complete-operation raw read API, and pins the rotated backend.
Atomic publication, namespace, ownership, and no-replay rules are unchanged,
so these execution-critical bytes entered `REVIEW_PENDING_NOT_ACTIVE`.
Fresh exact-byte review returned `PASS_GO`; the owner remains inactive.

## Deliberate non-claims and next gates

`raw_evidence_durable=true` means only that this owner can durably publish and
strictly re-read a supplied command return while its H0 gate is opened by
tests. The separate review-pending execution join now calls it in host
fixtures, but `integrated_live_consumer=false` remains explicit. A host crash after a device
command but before the first raw publication remains represented only by the
pre-existing effect intent and must never cause replay.

The current review-pending unit connects the fixed command-return hook, derives
missing journal results without command replay, and covers absent/partial cuts.
It still requires independent executable review, a separately reviewed
physical-entry bridge, target-contract amendment, and mechanical activation.
Only after those gates may a fresh connected prepare and approval be created.

No device, USB endpoint, ADB, `su`, Odin, network, private live run, reboot, or
partition transfer was contacted by this H0 unit.
